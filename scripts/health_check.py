#!/usr/bin/env python3
"""
Growww Discovery Engine – CLI Health & Diagnostics Tool (Phase 8)
Returns exit code 0 if healthy, exit code 1 if degraded/unhealthy.
"""

import os
import sys
import json
import argparse

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from services.health_service import HealthService

def main():
    parser = argparse.ArgumentParser(description="Run Growww Investor Discovery Engine health check.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format for monitoring agents")
    args = parser.parse_args()

    service = HealthService()
    report = service.run_full_diagnostics()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = report["overall_status"]
        print("=" * 80)
        print(f"GROWWW INVESTOR DISCOVERY ENGINE – HEALTH DIAGNOSTICS: [{status}]")
        print(f"Timestamp: {report['timestamp']}")
        print(f"Diagnostics duration: {report['diagnostics_duration_ms']}ms")
        print("=" * 80)

        for check_name, check_data in report["checks"].items():
            st = check_data.get("status", "UNKNOWN")
            print(f" - {check_name:<25}: [{st}]")
            for k, v in check_data.items():
                if k != "status":
                    print(f"      {k}: {v}")

        print("=" * 80)

    if report["overall_status"] == "UNHEALTHY":
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
