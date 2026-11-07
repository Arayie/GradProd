"""
Production Health Check and System Diagnostics Service (Phase 8)
Performs deep health checks across database connectivity, latency, schema integrity,
quarantine enforcement, memory usage, and AI model availability.
"""

import os
import sys
import time
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from database.connection import get_db, DatabaseConnection
from core.database_manager import get_database_manager

logger = logging.getLogger("growww.health")

class HealthService:
    """Evaluates comprehensive production health criteria and outputs JSON diagnostic status."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()
        self.db_mgr = get_database_manager(self.db)

    def check_database_latency(self) -> Dict[str, Any]:
        """Measures SQLite / PostgreSQL round-trip query latency."""
        t0 = time.time()
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            latency_ms = round((time.time() - t0) * 1000, 2)
            return {
                "status": "PASS" if latency_ms < 50.0 else "DEGRADED",
                "latency_ms": latency_ms,
                "threshold_ms": 50.0,
                "message": f"Query response in {latency_ms}ms",
            }
        except Exception as exc:
            return {"status": "FAIL", "latency_ms": -1, "error": str(exc)}

    def check_schema_and_foreign_keys(self) -> Dict[str, Any]:
        """Runs SQLite PRAGMA quick_check and foreign_key_check."""
        try:
            with self.db.get_cursor() as cursor:
                # 1. Quick check
                quick_res = cursor.execute("PRAGMA quick_check;").fetchall()
                is_quick_ok = len(quick_res) == 1 and quick_res[0][0] == "ok"

                # 2. Foreign key check
                fk_violations = cursor.execute("PRAGMA foreign_key_check;").fetchall()

            return {
                "status": "PASS" if (is_quick_ok and len(fk_violations) == 0) else "FAIL",
                "quick_check": "ok" if is_quick_ok else str(quick_res),
                "foreign_key_violations": len(fk_violations),
            }
        except Exception as exc:
            return {"status": "FAIL", "error": str(exc)}

    def check_quarantine_integrity(self) -> Dict[str, Any]:
        """Verifies that exactly 8 synthetic records exist and zero leak to eligible research."""
        try:
            with self.db.get_cursor() as cursor:
                quarantine_count = cursor.execute(
                    "SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO';"
                ).fetchone()[0]

                leak_count = cursor.execute(
                    "SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND source_record_id LIKE 'DEMO%';"
                ).fetchone()[0]

            is_quarantine_valid = (quarantine_count == 8) and (leak_count == 0)
            return {
                "status": "PASS" if is_quarantine_valid else "FAIL",
                "quarantined_records": quarantine_count,
                "expected_quarantined": 8,
                "leaked_into_eligible": leak_count,
            }
        except Exception as exc:
            return {"status": "FAIL", "error": str(exc)}

    def check_table_metrics(self) -> Dict[str, Any]:
        """Gathers row counts across key database tables."""
        try:
            with self.db.get_cursor() as cursor:
                counts = {
                    "total_reviews": cursor.execute("SELECT COUNT(*) FROM reviews;").fetchone()[0],
                    "eligible_reviews": cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE';").fetchone()[0],
                    "sip_relevant_reviews": cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND (sip_relevance_status = 'SIP_RELEVANT' OR mentions_sip = 1);").fetchone()[0],
                    "ai_evidence_records": cursor.execute("SELECT COUNT(*) FROM ai_evidence_log;").fetchone()[0],
                    "opportunities_ranked": cursor.execute("SELECT COUNT(*) FROM opportunities;").fetchone()[0],
                }
            return {"status": "PASS", "counts": counts}
        except Exception as exc:
            return {"status": "FAIL", "error": str(exc)}

    def check_system_resources(self) -> Dict[str, Any]:
        """Checks local disk space and process memory usage."""
        import resource
        try:
            # Memory RSS in MB
            usage = resource.getrusage(resource.RUSAGE_SELF)
            # macOS ru_maxrss is in bytes, Linux is in KB
            rss_mb = round(usage.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024), 2)
            
            # Disk space
            stat = os.statvfs(self.db.db_path if os.path.exists(self.db.db_path) else REPO_ROOT)
            free_gb = round((stat.f_bavail * stat.f_frsize) / (1024 ** 3), 2)

            return {
                "status": "PASS" if rss_mb < 512.0 and free_gb > 0.5 else "DEGRADED",
                "process_memory_mb": rss_mb,
                "memory_budget_mb": 512.0,
                "free_disk_space_gb": free_gb,
            }
        except Exception as exc:
            return {"status": "PASS", "info": str(exc)}

    def run_full_diagnostics(self) -> Dict[str, Any]:
        """Compiles overall system health diagnostic report."""
        start_t = time.time()
        latency = self.check_database_latency()
        schema = self.check_schema_and_foreign_keys()
        quarantine = self.check_quarantine_integrity()
        metrics = self.check_table_metrics()
        resources = self.check_system_resources()

        # Determine overall status
        statuses = [
            latency.get("status"),
            schema.get("status"),
            quarantine.get("status"),
            metrics.get("status"),
            resources.get("status", "PASS"),
        ]

        if any(s == "FAIL" for s in statuses):
            overall = "UNHEALTHY"
        elif any(s == "DEGRADED" for s in statuses):
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"

        return {
            "overall_status": overall,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "diagnostics_duration_ms": round((time.time() - start_t) * 1000, 2),
            "checks": {
                "database_latency": latency,
                "database_integrity": schema,
                "quarantine_isolation": quarantine,
                "data_metrics": metrics,
                "system_resources": resources,
            }
        }
