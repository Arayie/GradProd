"""
Live Multi-Application Review Collection Script for Growww Discovery Engine.
Orchestrates collection across all 8 registered Indian investment apps via Apple's public RSS feed.
Enforces per-page persistence, deduplication, PII stripping, audit run logging, and checkpointing.
"""
import os
import sys
import json
import time
from datetime import datetime

# Setup workspace and lib path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(WORKSPACE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from database.connection import get_db
from database.repositories import ReviewRepository, CheckpointRepository, IngestionRunRepository
from core.config_loader import get_config_loader
from services.ingestion_service import CommonIngestionService

def run_collection():
    print("=" * 80)
    print("GROWWW INVESTOR DISCOVERY ENGINE - PHASE 2 REVIEW COLLECTION")
    print("Executing Two-Store MVP: Apple App Store Public RSS Feed (India Storefront)")
    print("=" * 80)

    db = get_db()
    service = CommonIngestionService(db=db)
    config_loader = get_config_loader()
    apps = config_loader.get_registered_apps()

    print(f"\nFound {len(apps)} registered applications in apps.yml:")
    for a in apps:
        app_id = a.get("internal_id")
        name = a.get("official_name")
        apple_id = a.get("apple_app_store", {}).get("app_id")
        print(f" - [{app_id}] {name} (Apple App ID: {apple_id})")

    results = {}
    overall_start = time.time()

    print("\nStarting paginated collection (up to 10 pages / 500 reviews per application)...")
    print("-" * 80)

    for idx, a in enumerate(apps, 1):
        app_id = a.get("internal_id")
        app_name = a.get("official_name")
        apple_id = a.get("apple_app_store", {}).get("app_id")

        print(f"\n[{idx}/{len(apps)}] Collecting reviews for: {app_name} ({app_id})...")
        t0 = time.time()

        try:
            res = service.ingest_apple_rss(
                app_id=app_id,
                max_pages=10,
                stop_on_checkpoint=False,  # Full collection across all 10 pages
                admin_override=True
            )
            elapsed = time.time() - t0
            results[app_id] = res

            print(f"    Status: {res['status']}")
            print(f"    Pages retrieved: {res['pages_retrieved']} / 10")
            print(f"    Reviews fetched from Apple: {res['reviews_received']}")
            print(f"    New unique reviews accepted: {res['accepted_count']}")
            print(f"    Duplicates skipped: {res['duplicate_count']}")
            print(f"    Coverage date range: {res['oldest_review_date']} to {res['newest_review_date']}")
            print(f"    Coverage duration: {res['coverage_duration_days']} days (~{res['coverage_duration_days'] / 30.4:.1f} months)")
            if res.get("errors"):
                print(f"    Warnings/Notices: {res['errors']}")
            print(f"    Completed in {elapsed:.2f}s")

        except Exception as exc:
            elapsed = time.time() - t0
            print(f"    FAILED: {exc} (in {elapsed:.2f}s)")
            results[app_id] = {
                "app_id": app_id,
                "status": "FAILED",
                "error": str(exc),
                "reviews_received": 0,
                "accepted_count": 0,
                "duplicate_count": 0,
                "coverage_duration_days": 0
            }

        # Polite delay between apps
        time.sleep(0.5)

    total_time = time.time() - overall_start
    print("\n" + "=" * 80)
    print("COLLECTION COMPLETED")
    print(f"Total time elapsed: {total_time:.2f}s")
    print("=" * 80)

    # Database summary
    rev_repo = ReviewRepository(db)
    metrics = rev_repo.get_summary_metrics()

    print("\nDATABASE STATE SUMMARY:")
    print(f" - Total database records: {metrics['total_records']}")
    print(f" - Genuine eligible reviews: {metrics['genuine_reviews']}")
    print(f" - Quarantined synthetic demo records: {metrics['demo_reviews']}")
    print(f" - Rejected records: {metrics['rejected_reviews']}")
    print(f" - Pending verification: {metrics['pending_reviews']}")

    print("\nAPP DISTRIBUTION (GENUINE REVIEWS):")
    for app_id, count in sorted(metrics.get("app_distribution", {}).items(), key=lambda x: -x[1]):
        print(f" - {app_id:15s}: {count:5d} reviews")

    print("\nRATING DISTRIBUTION (GENUINE REVIEWS):")
    for star, count in sorted(metrics.get("rating_distribution", {}).items()):
        pct = (count / metrics['genuine_reviews'] * 100) if metrics['genuine_reviews'] > 0 else 0
        print(f" - {star} Star: {count:5d} ({pct:5.1f}%)")

    # Sync CSV exports
    service.run_logger.export_to_csv()
    service.run_logger.export_errors_to_csv()
    print("\nRun logs exported to outputs/ingestion_runs.csv")
    print("Error logs exported to outputs/collection_errors.csv")

if __name__ == "__main__":
    run_collection()
