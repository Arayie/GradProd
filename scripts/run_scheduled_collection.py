#!/usr/bin/env python3
"""
Growww Discovery Engine – Scheduled Collection Runner (Phase 8)
CLI tool for executing scheduled review refresh cycles via cron or standalone daemon.
"""

import os
import sys
import argparse
import time
import json
from datetime import datetime

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from services.scheduler_service import ScheduledRefreshService
from core.database_manager import get_database_manager

def main():
    parser = argparse.ArgumentParser(description="Run scheduled review ingestion for Growww Discovery Engine.")
    parser.add_argument("--pages", type=int, default=3, help="Max pages per app (default: 3)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--interval-hours", type=int, default=168, help="Interval in hours for daemon mode (default: 168 = 1 week)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run: verify configuration and access without writes")
    args = parser.parse_args()

    print("=" * 80)
    print("GROWWW INVESTOR DISCOVERY ENGINE – SCHEDULED DATA REFRESH")
    print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    service = ScheduledRefreshService()

    if args.dry_run:
        print("[*] Performing dry-run compliance and connection check...")
        service.verify_no_appfollow_or_scraping()
        db_health = get_database_manager().check_health()
        print(f"[+] Database status: {db_health.get('status')}")
        print(f"[+] Current total records: {db_health.get('total_records')}")
        print("[+] Dry-run completed: all compliance rules satisfied!")
        return

    def run_cycle():
        print(f"\n[*] Executing collection cycle (max_pages={args.pages})...")
        report = service.execute_scheduled_refresh(max_pages=args.pages)
        print("\n" + "=" * 80)
        print(f"CYCLE RESULT: {report['status']}")
        print(f"Apps Attempted:          {report['apps_attempted']}")
        print(f"Apps Successful:         {report['apps_successful']}")
        print(f"New Reviews Ingested:    {report['new_reviews_ingested']}")
        print(f"Duplicates Skipped:      {report['duplicate_reviews_skipped']}")
        print(f"CSV Files Processed:     {report['csv_files_processed']}")
        print(f"Execution Duration:      {report['duration_seconds']}s")
        if report["errors"]:
            print(f"Errors Encountered:      {len(report['errors'])}")
            for err in report["errors"]:
                print(f"  - {err}")
        print("=" * 80)

    if args.daemon:
        print(f"[*] Starting daemon mode. Refresh interval: {args.interval_hours} hours.")
        while True:
            run_cycle()
            sleep_secs = args.interval_hours * 3600
            print(f"[*] Sleeping for {args.interval_hours} hours until next cycle...")
            time.sleep(sleep_secs)
    else:
        run_cycle()

if __name__ == "__main__":
    main()
