"""
Common Ingestion Service for Growww Discovery Engine.
Orchestrates Apple RSS and Manual CSV collection through a unified pipeline:
Source -> Access Gate -> Validation -> Normalization -> Deduplication -> Persistence -> Run Logging.
"""
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import get_db, DatabaseConnection
from database.repositories import (
    ReviewRepository, AppRepository, SourceRouteRepository,
    CheckpointRepository, ImportBatchRepository
)
from core.config_loader import get_config_loader, ConfigLoader
from core.exceptions import ValidationError, SecurityViolationError, SourcePermissionError
from ingestion.apple_app_store_rss import AppleRSSConnector
from ingestion.manual_review_csv import ManualReviewCSVImporter
from ingestion.deduplicate import Deduplicator
from ingestion.run_logger import IngestionRunLogger, get_run_logger

class CommonIngestionService:
    """Unified ingestion service integrating all approved review sources into canonical storage."""

    def __init__(
        self,
        db: Optional[DatabaseConnection] = None,
        config_loader: Optional[ConfigLoader] = None
    ):
        self.db = db or get_db()
        self.config_loader = config_loader or get_config_loader()
        self.app_repo = AppRepository(self.db)
        self.source_repo = SourceRouteRepository(self.db)
        self.review_repo = ReviewRepository(self.db)
        self.checkpoint_repo = CheckpointRepository(self.db)
        self.batch_repo = ImportBatchRepository(self.db)
        self.deduplicator = Deduplicator(self.review_repo)
        self.run_logger = IngestionRunLogger(self.db)
        self.apple_connector = AppleRSSConnector(checkpoint_repo=self.checkpoint_repo)
        self.csv_importer = ManualReviewCSVImporter()

    def _verify_app_exists(self, app_id: str) -> Dict[str, Any]:
        """Ensures application is registered in database or config."""
        app = self.app_repo.get_by_internal_id(app_id)
        if not app:
            # Fallback to config lookup
            app = self.config_loader.get_app_by_id(app_id)
            if not app:
                raise ValidationError(f"Unregistered application: '{app_id}'. Application must exist in apps.yml.")
        return app

    def _check_access_gate(self, source_id: str, admin_override: bool = False) -> Dict[str, Any]:
        """
        Validates source route permissions and enabled state.
        Throws SourcePermissionError if route is disabled or unauthorized.
        """
        sources = self.config_loader.get_all_sources()
        src = next((s for s in sources if s.get("source_id") == source_id), None)
        if not src:
            raise SourcePermissionError(f"Unknown source route: '{source_id}'")

        perm_status = src.get("permission_status")
        is_enabled = src.get("enabled", False)

        # Check if enabled dynamically in database
        if not is_enabled:
            db_route = self.source_repo.get_by_source_id(source_id)
            if db_route and db_route.get("enabled"):
                is_enabled = True

        if perm_status == "REJECTED":
            raise SourcePermissionError(f"Source route '{source_id}' is REJECTED by data governance policy.")

        if not is_enabled and not admin_override:
            raise SourcePermissionError(
                f"Source route '{source_id}' is DISABLED by default (permission_status: {perm_status}). "
                "Explicit activation or administrative authorization is required before execution."
            )

        return src

    # =========================================================================
    # =========================================================================
    # ROUTE A: Apple App Store RSS Automated Collection
    # =========================================================================
    def ingest_apple_rss(
        self,
        app_id: str,
        max_pages: int = 10,
        stop_on_checkpoint: bool = True,
        admin_override: bool = False
    ) -> Dict[str, Any]:
        """
        Executes an automated ingestion run for an application via Apple's public RSS feed.
        Persists each retrieved page immediately into SQLite for resilience.
        """
        app = self._verify_app_exists(app_id)
        
        # Access Gate Check
        source_route = self._check_access_gate("apple_app_store_public_rss", admin_override=admin_override)

        # Ensure Apple ID exists
        apple_id = app.get("apple_app_id") or app.get("apple_app_store", {}).get("app_id")
        if not apple_id:
            raise ValidationError(f"Application '{app_id}' has no registered Apple App ID.")

        # Start Ingestion Run
        run_id = self.run_logger.start_run(
            app_id=app_id,
            store="apple_app_store",
            collection_method="apple_app_store_rss",
            requested_count=max_pages * 50
        )

        app_config = {
            "internal_id": app_id,
            "apple_app_store": {"app_id": str(apple_id)},
            "storefront": app.get("storefront", "IN")
        }

        # Reset deduplicator for new batch
        self.deduplicator.reset_batch_cache()

        accepted_count = 0
        duplicate_count = 0
        rejected_count = 0
        all_raw_reviews = []

        def persist_page_reviews(page_num: int, page_reviews: List[Dict[str, Any]]):
            nonlocal accepted_count, duplicate_count, rejected_count, all_raw_reviews
            if not page_reviews:
                return

            all_raw_reviews.extend(page_reviews)
            # Transactional persistence into canonical reviews table per page
            with self.db.get_connection():
                for rev in page_reviews:
                    rev["collection_run_id"] = run_id
                    rev["source_permission_id"] = source_route.get("approval_reference", "PHASE0-AUDIT-APPLE-RSS-001")

                    # Deduplication check
                    is_dup = self.deduplicator.is_duplicate(
                        app_id=app_id,
                        store="apple_app_store",
                        source_record_id=rev.get("source_record_id"),
                        content_hash=rev.get("content_hash"),
                        raw_text=rev.get("review_text")
                    )

                    if is_dup:
                        duplicate_count += 1
                        continue

                    try:
                        self.review_repo.insert_review(rev)
                        self.deduplicator.mark_seen(
                            app_id=app_id,
                            store="apple_app_store",
                            source_record_id=rev.get("source_record_id"),
                            content_hash=rev.get("content_hash")
                        )
                        accepted_count += 1
                    except Exception as ins_err:
                        rejected_count += 1
                        self.run_logger.log_error(
                            source_name="apple_app_store_rss",
                            error_type=type(ins_err).__name__,
                            error_message=str(ins_err),
                            run_id=run_id
                        )

        try:
            collection_result = self.apple_connector.collect_app_reviews(
                app_config=app_config,
                max_pages=max_pages,
                stop_on_checkpoint=stop_on_checkpoint,
                on_page_collected=persist_page_reviews
            )

            # Log collection HTTP errors if any
            for http_err in collection_result.get("http_errors", []):
                self.run_logger.log_error(
                    source_name="apple_app_store_rss",
                    error_type="HTTPError",
                    error_message=http_err,
                    run_id=run_id
                )

            # Finalize Run Record
            self.run_logger.finish_run(
                run_id=run_id,
                received_count=len(all_raw_reviews),
                accepted_count=accepted_count,
                duplicate_count=duplicate_count,
                rejected_count=rejected_count,
                coverage_start=collection_result.get("oldest_review_date"),
                coverage_end=collection_result.get("newest_review_date"),
                error_summary="; ".join(collection_result.get("http_errors", [])) or None,
                status=collection_result.get("status", "COMPLETED")
            )

            return {
                "run_id": run_id,
                "app_id": app_id,
                "store": "apple_app_store",
                "status": collection_result.get("status", "COMPLETED"),
                "pages_retrieved": collection_result.get("pages_retrieved", 0),
                "reviews_received": len(all_raw_reviews),
                "accepted_count": accepted_count,
                "duplicate_count": duplicate_count,
                "rejected_count": rejected_count,
                "newest_review_date": collection_result.get("newest_review_date"),
                "oldest_review_date": collection_result.get("oldest_review_date"),
                "coverage_duration_days": collection_result.get("coverage_duration_days", 0),
                "hit_checkpoint": collection_result.get("hit_checkpoint", False),
                "errors": collection_result.get("http_errors", [])
            }

        except Exception as exc:
            self.run_logger.log_error(
                source_name="apple_app_store_rss",
                error_type=type(exc).__name__,
                error_message=str(exc),
                run_id=run_id
            )
            self.run_logger.finish_run(
                run_id=run_id,
                received_count=len(all_raw_reviews),
                accepted_count=accepted_count,
                duplicate_count=duplicate_count,
                rejected_count=rejected_count,
                error_summary=str(exc),
                status="FAILED"
            )
            raise

    def ingest_all_apple_apps(
        self,
        max_pages: int = 10,
        stop_on_checkpoint: bool = False,
        admin_override: bool = False,
        delay_between_apps: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes Apple RSS ingestion across all 8 registered applications in config/apps.yml.
        Enforces polite delay between applications and accumulates full coverage summary.
        """
        apps = self.config_loader.get_registered_apps()
        summaries = {}
        total_received = 0
        total_accepted = 0
        total_duplicates = 0
        total_rejected = 0
        all_errors = []

        for app in apps:
            app_id = app.get("internal_id")
            apple_cfg = app.get("apple_app_store", {})
            apple_id = apple_cfg.get("app_id")
            if not apple_id:
                continue

            try:
                res = self.ingest_apple_rss(
                    app_id=app_id,
                    max_pages=max_pages,
                    stop_on_checkpoint=stop_on_checkpoint,
                    admin_override=admin_override
                )
                summaries[app_id] = res
                total_received += res.get("reviews_received", 0)
                total_accepted += res.get("accepted_count", 0)
                total_duplicates += res.get("duplicate_count", 0)
                total_rejected += res.get("rejected_count", 0)
                if res.get("errors"):
                    all_errors.extend(res["errors"])
            except Exception as e:
                err_msg = f"Failed ingestion for {app_id}: {str(e)}"
                all_errors.append(err_msg)
                summaries[app_id] = {
                    "app_id": app_id,
                    "status": "FAILED",
                    "error": str(e),
                    "accepted_count": 0,
                    "reviews_received": 0
                }

            if delay_between_apps > 0:
                time.sleep(delay_between_apps)

        return {
            "total_apps": len(summaries),
            "total_received": total_received,
            "total_accepted": total_accepted,
            "total_duplicates": total_duplicates,
            "total_rejected": total_rejected,
            "app_summaries": summaries,
            "errors": all_errors
        }

    # =========================================================================
    # ROUTE B: Manual Review CSV Ingestion
    # =========================================================================
    def ingest_manual_csv(
        self,
        file_or_path: Any,
        filename: str,
        app_id: str,
        store: str,
        provenance_confirmed: bool,
        permission_status: str = "PENDING_VERIFICATION",
        source_description: str = "",
        column_mapping: Optional[Dict[str, str]] = None,
        is_synthetic: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests and validates a customer review CSV dataset through the common ingestion pipeline.
        """
        self._verify_app_exists(app_id)

        # Access Gate Check
        source_route = self._check_access_gate("manual_review_csv_import", admin_override=True)

        # Start Run Logger session
        run_id = self.run_logger.start_run(
            app_id=app_id,
            store=store,
            collection_method="manual_csv_import"
        )

        try:
            parsed_result = self.csv_importer.parse_dataset(
                file_or_path=file_or_path,
                filename=filename,
                app_id=app_id,
                store=store,
                provenance_confirmed=provenance_confirmed,
                permission_status=permission_status,
                source_description=source_description,
                column_mapping=column_mapping,
                is_synthetic=is_synthetic
            )

            batch_id = parsed_result["batch_id"]
            raw_reviews = parsed_result["reviews"]
            rejected_rows = parsed_result["rejected_rows_details"]

            # Initialize Batch Record in SQLite
            self.batch_repo.create_batch({
                "batch_id": batch_id,
                "original_filename": filename,
                "app_id": app_id,
                "store": store,
                "source_description": source_description,
                "permission_status": permission_status,
                "total_rows": parsed_result["total_rows"],
                "batch_status": "PROCESSING"
            })

            accepted_count = 0
            duplicate_count = 0
            newest_date = None
            oldest_date = None

            self.deduplicator.reset_batch_cache()

            # Transactional persistence into canonical reviews table
            with self.db.get_connection():
                for rev in raw_reviews:
                    rev["collection_run_id"] = run_id

                    # Deduplication check
                    is_dup = self.deduplicator.is_duplicate(
                        app_id=app_id,
                        store=store,
                        source_record_id=rev.get("source_record_id"),
                        content_hash=rev.get("content_hash"),
                        raw_text=rev.get("review_text")
                    )

                    if is_dup:
                        duplicate_count += 1
                        continue

                    try:
                        self.review_repo.insert_review(rev)
                        self.deduplicator.mark_seen(
                            app_id=app_id,
                            store=store,
                            source_record_id=rev.get("source_record_id"),
                            content_hash=rev.get("content_hash")
                        )
                        accepted_count += 1

                        # Track dates
                        r_date = rev.get("review_created_at")
                        if r_date:
                            if not newest_date or str(r_date) > str(newest_date):
                                newest_date = str(r_date)
                            if not oldest_date or str(r_date) < str(oldest_date):
                                oldest_date = str(r_date)

                    except Exception as ins_err:
                        rejected_rows.append({
                            "row_number": accepted_count + duplicate_count + len(rejected_rows) + 1,
                            "errors": [f"Database error: {ins_err}"],
                            "raw_data": rev
                        })
                        self.run_logger.log_error(
                            source_name="manual_csv_import",
                            error_type=type(ins_err).__name__,
                            error_message=str(ins_err),
                            run_id=run_id
                        )

            # Update Batch Record
            final_batch_status = "COMPLETED" if (accepted_count > 0 or duplicate_count > 0) else "FAILED"
            self.batch_repo.update_batch_stats(
                batch_id=batch_id,
                accepted=accepted_count,
                rejected=len(rejected_rows),
                duplicates=duplicate_count,
                status=final_batch_status
            )

            # Finalize Ingestion Run
            self.run_logger.finish_run(
                run_id=run_id,
                received_count=parsed_result["total_rows"],
                accepted_count=accepted_count,
                duplicate_count=duplicate_count,
                rejected_count=len(rejected_rows),
                coverage_start=oldest_date,
                coverage_end=newest_date,
                error_summary=f"{len(rejected_rows)} validation rejections" if rejected_rows else None,
                status=final_batch_status
            )

            return {
                "run_id": run_id,
                "batch_id": batch_id,
                "app_id": app_id,
                "store": store,
                "total_rows": parsed_result["total_rows"],
                "accepted_count": accepted_count,
                "duplicate_count": duplicate_count,
                "rejected_count": len(rejected_rows),
                "eligibility_status": parsed_result["eligibility_status"],
                "newest_review_date": newest_date,
                "oldest_review_date": oldest_date,
                "rejected_rows_details": rejected_rows
            }

        except Exception as exc:
            self.run_logger.log_error(
                source_name="manual_csv_import",
                error_type=type(exc).__name__,
                error_message=str(exc),
                run_id=run_id
            )
            self.run_logger.finish_run(
                run_id=run_id,
                received_count=0,
                accepted_count=0,
                duplicate_count=0,
                rejected_count=0,
                error_summary=str(exc),
                status="FAILED"
            )
            raise

_ingestion_service = None

def get_common_ingestion_service(
    db: Optional[DatabaseConnection] = None,
    config_loader: Optional[ConfigLoader] = None
) -> CommonIngestionService:
    """Returns singleton instance of CommonIngestionService."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = CommonIngestionService(db, config_loader)
    return _ingestion_service
