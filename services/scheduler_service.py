"""
Automated Scheduled Data Refresh Service (Phase 8)
Orchestrates scheduled review ingestion across permitted sources (Apple RSS + CSV drops).
Enforces exponential backoff, AppFollow rejection, deduplication, and India Standard Time (IST) tracking.
"""

import os
import sys
import time
import glob
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from database.connection import get_db, DatabaseConnection
from database.repositories import ReviewRepository, CheckpointRepository, IngestionRunRepository
from core.config_loader import get_config_loader, ConfigLoader
from services.ingestion_service import CommonIngestionService

logger = logging.getLogger("growww.scheduler")

class ScheduledRefreshService:
    """Production scheduler executing incremental ingestion with resilience and retry logic."""

    def __init__(self, db: DatabaseConnection = None, config_loader: ConfigLoader = None):
        self.db = db or get_db()
        self.config_loader = config_loader or get_config_loader()
        self.ingestion_service = CommonIngestionService(db=self.db, config_loader=self.config_loader)
        self.review_repo = ReviewRepository(self.db)
        self.run_repo = IngestionRunRepository(self.db)
        self.checkpoint_repo = CheckpointRepository(self.db)

    def verify_no_appfollow_or_scraping(self):
        """Strict governance check: ensures no paid AppFollow or HTML scrapers are configured."""
        sources = self.config_loader.get_all_sources()
        for s in sources:
            source_id = s.get("source_id", "").lower()
            collector_type = s.get("collector_type", "").lower()
            if "appfollow" in source_id or "appfollow" in collector_type:
                if s.get("enabled", False):
                    raise PermissionError(
                        f"CRITICAL COMPLIANCE VIOLATION: Source '{source_id}' references AppFollow. "
                        "AppFollow is permanently rejected and prohibited under PRD zero-paid-API mandate."
                    )
            if "scraper" in source_id or "scrape" in collector_type:
                if s.get("enabled", False):
                    raise PermissionError(
                        f"CRITICAL COMPLIANCE VIOLATION: Source '{source_id}' specifies HTML scraper. "
                        "HTML scraping of app stores is strictly prohibited."
                    )

    def execute_scheduled_refresh(self, max_pages: int = 5, import_csv_dir: str = None) -> Dict[str, Any]:
        """
        Executes a complete scheduled collection cycle:
        1. Verifies zero prohibited sources.
        2. Pulls latest reviews via Apple RSS with 3x retry and backoff.
        3. Ingests any pending Google Play CSV drops in import_csv_dir.
        4. Incremental deduplication and audit run recording.
        """
        self.verify_no_appfollow_or_scraping()

        start_time = time.time()
        ist_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        report = {
            "execution_timestamp": ist_now,
            "apps_attempted": 0,
            "apps_successful": 0,
            "new_reviews_ingested": 0,
            "duplicate_reviews_skipped": 0,
            "csv_files_processed": 0,
            "errors": [],
            "status": "SUCCESS",
            "duration_seconds": 0.0,
        }

        apps = self.config_loader.get_registered_apps()

        # 1. Process Apple App Store RSS for each registered application
        for app in apps:
            app_id = app.get("internal_id")
            app_name = app.get("official_name")
            apple_config = app.get("apple_app_store", {})
            apple_app_id = apple_config.get("app_id")

            if not apple_app_id:
                continue

            report["apps_attempted"] += 1
            success = False
            retries = 3

            for attempt in range(1, retries + 1):
                try:
                    logger.info(f"Ingesting Apple RSS for {app_name} ({app_id}), attempt {attempt}/{retries}")
                    res = self.ingestion_service.ingest_apple_rss(
                        app_id=app_id,
                        max_pages=max_pages,
                        admin_override=False,
                    )
                    report["new_reviews_ingested"] += res.get("inserted", 0)
                    report["duplicate_reviews_skipped"] += res.get("duplicates", 0)
                    report["apps_successful"] += 1
                    success = True
                    break
                except Exception as exc:
                    logger.warning(f"Attempt {attempt} failed for {app_id}: {exc}")
                    if attempt < retries:
                        time.sleep(2 ** attempt)  # 2s, 4s backoff
                    else:
                        report["errors"].append({
                            "app_id": app_id,
                            "error": str(exc),
                            "timestamp": datetime.utcnow().isoformat(),
                        })

        # 2. Check for staged CSV import drops
        csv_dir = import_csv_dir or os.path.join(REPO_ROOT, "data", "imports")
        if os.path.exists(csv_dir):
            pending_csvs = glob.glob(os.path.join(csv_dir, "*.csv"))
            for csv_file in pending_csvs:
                try:
                    csv_res = self.ingestion_service.ingest_manual_csv(
                        csv_file_path=csv_file,
                        source_id="google_play_csv_import",
                    )
                    report["new_reviews_ingested"] += csv_res.get("valid_records", 0)
                    report["csv_files_processed"] += 1
                    # Archive processed file
                    processed_dir = os.path.join(csv_dir, "processed")
                    os.makedirs(processed_dir, exist_ok=True)
                    dest = os.path.join(processed_dir, os.path.basename(csv_file))
                    os.replace(csv_file, dest)
                except Exception as exc:
                    report["errors"].append({
                        "file": csv_file,
                        "error": str(exc),
                        "timestamp": datetime.utcnow().isoformat(),
                    })

        report["duration_seconds"] = round(time.time() - start_time, 2)
        if report["errors"]:
            report["status"] = "PARTIAL_SUCCESS" if report["apps_successful"] > 0 else "FAILED"

        return report
