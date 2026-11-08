#!/usr/bin/env python3
"""
Growww – Production PostgreSQL Connection & SSL Verification Script
Verifies:
1. Secrets / environment retrieval of DATABASE_URL
2. URL normalization (postgresql+psycopg2://)
3. Strict sslmode=require enforcement
4. Hostname resolution
5. PostgreSQL connection establishment
6. SELECT 1 execution
7. PostgreSQL server version inspection
8. Database identity verification
9. Table accessibility and row count validation
"""

import os
import sys
import socket
import argparse
import logging
from typing import Dict, Any

# Ensure workspace root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from database.connection import (
    DatabaseConnection,
    get_env_database_url_with_source,
    normalize_database_url,
    get_connection_diagnostics,
    mask_connection_url,
)

REQUIRED_TABLES = [
    "apps",
    "source_routes",
    "import_batches",
    "ingestion_runs",
    "collection_errors",
    "collection_checkpoints",
    "reviews",
    "ai_evidence_log",
    "human_adjudications",
    "opportunities",
    "opportunity_audits",
]

def run_verification(pg_url: str = None) -> Dict[str, Any]:
    print("=" * 80)
    print("GROWWW DISCOVERY ENGINE – PRODUCTION POSTGRESQL SSL VERIFICATION")
    print("=" * 80)

    results = {
        "step_1_url_retrieval": False,
        "step_2_url_normalization": False,
        "step_3_sslmode_require": False,
        "step_4_dns_resolution": False,
        "step_5_connection_established": False,
        "step_6_select_1": False,
        "step_7_server_version": None,
        "step_8_database_identity": None,
        "step_9_tables_verified": False,
        "table_counts": {},
        "diagnostics": {},
        "error": None,
    }

    # Step 1: Retrieve DATABASE_URL
    print("\n[*] STEP 1: Retrieving DATABASE_URL...")
    if pg_url:
        raw_url = pg_url.strip()
        source = "command_line_argument"
    else:
        raw_url, source = get_env_database_url_with_source()

    if not raw_url:
        print("[!] ERROR: No DATABASE_URL found in Streamlit secrets or environment variables.")
        results["error"] = "DATABASE_URL not configured"
        return results

    results["step_1_url_retrieval"] = True
    masked_raw = mask_connection_url(raw_url)
    print(f"    [+] Successfully retrieved DATABASE_URL from: {source}")
    print(f"    [+] Masked URL: {masked_raw}")

    # Step 2: Normalize URL
    print("\n[*] STEP 2: Normalizing PostgreSQL URL for SQLAlchemy/psycopg2...")
    norm_url = normalize_database_url(raw_url)
    masked_norm = mask_connection_url(norm_url)
    if not norm_url.startswith("postgresql+psycopg2://"):
        print(f"[!] ERROR: Normalized URL does not use postgresql+psycopg2:// driver: {masked_norm}")
        results["error"] = "Driver dialect mismatch"
        return results

    results["step_2_url_normalization"] = True
    print(f"    [+] Normalized Driver Dialect: postgresql+psycopg2://")

    # Step 3: Verify sslmode=require
    print("\n[*] STEP 3: Verifying strict SSL configuration...")
    diag = get_connection_diagnostics(norm_url, source)
    results["diagnostics"] = diag
    if diag.get("sslmode") != "require":
        print(f"[!] ERROR: SSL mode is '{diag.get('sslmode')}', expected 'require'.")
        results["error"] = "SSL mode not require"
        return results

    results["step_3_sslmode_require"] = True
    print(f"    [+] SSL Mode strictly enforced: {diag['sslmode']}")
    print(f"    [+] Target Hostname: {diag['hostname']}:{diag['port']}")
    print(f"    [+] Database Name:   {diag['database']}")

    # Step 4: Resolve Hostname
    print(f"\n[*] STEP 4: Resolving DNS for hostname '{diag['hostname']}'...")
    try:
        ip = socket.gethostbyname(diag["hostname"])
        results["step_4_dns_resolution"] = True
        print(f"    [+] DNS Resolution successful: {diag['hostname']} -> {ip}")
    except Exception as dns_err:
        print(f"[!] DNS Resolution Warning / Error: {dns_err}")
        # Could be inside sandbox without network access
        results["error"] = f"DNS Resolution failed: {dns_err}"

    # Step 5: Establish PostgreSQL Connection
    print("\n[*] STEP 5: Establishing PostgreSQL connection pool & checking out connection...")
    try:
        db = DatabaseConnection(db_path=norm_url)
        engine = db.get_engine()
        print(f"    [+] SQLAlchemy Engine created with connection pool:")
        print(f"        - pool_pre_ping: True")
        print(f"        - pool_size: 5, max_overflow: 10, pool_recycle: 300s")
        print(f"        - connect_timeout: 15s, keepalives: 1")

        with engine.connect() as conn:
            results["step_5_connection_established"] = True
            print("    [+] PostgreSQL connection established successfully over SSL!")

            # Step 6: Execute SELECT 1;
            print("\n[*] STEP 6: Executing SELECT 1 query...")
            from sqlalchemy import text
            s1 = conn.execute(text("SELECT 1;")).scalar()
            if s1 == 1:
                results["step_6_select_1"] = True
                print("    [+] Query SELECT 1 returned: 1")

            # Step 7: Server Version
            print("\n[*] STEP 7: Inspecting PostgreSQL server version...")
            version = conn.execute(text("SELECT version();")).scalar()
            results["step_7_server_version"] = version
            print(f"    [+] PostgreSQL Server Version: {version.split(',')[0]}")

            # Step 8: Database Identity
            print("\n[*] STEP 8: Verifying database name and connected user...")
            current_db = conn.execute(text("SELECT current_database();")).scalar()
            current_user = conn.execute(text("SELECT current_user;")).scalar()
            results["step_8_database_identity"] = {"database": current_db, "user": current_user}
            print(f"    [+] Active Database: '{current_db}' (User: '{current_user}')")

            # Step 9: Verify Tables
            print("\n[*] STEP 9: Verifying access to existing application tables...")
            existing_rows = conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            ).fetchall()
            existing_tables = {r[0].lower() for r in existing_rows}

            all_present = True
            for table in REQUIRED_TABLES:
                if table.lower() in existing_tables:
                    try:
                        cnt = conn.execute(text(f'SELECT COUNT(*) FROM "{table}";')).scalar()
                        results["table_counts"][table] = cnt
                        print(f"    [+] Table '{table:<22}': {cnt:>6} rows")
                    except Exception as cnt_err:
                        results["table_counts"][table] = f"error: {cnt_err}"
                        print(f"    [!] Table '{table:<22}': Error counting ({cnt_err})")
                else:
                    all_present = False
                    results["table_counts"][table] = "MISSING"
                    print(f"    [-] Table '{table:<22}': MISSING")

            results["step_9_tables_verified"] = all_present

    except Exception as exc:
        results["error"] = str(exc)
        print(f"\n[!] CONNECTION FAILURE: {type(exc).__name__}: {exc}")
        err_lower = str(exc).lower()
        if "ssl connection has been closed unexpectedly" in err_lower:
            print("\n[!] DIAGNOSTIC ADVICE: 'SSL connection has been closed unexpectedly'")
            print("    1. Render free-tier databases automatically spin down / sleep after 15 minutes of inactivity.")
            print("       The first connection may fail or timeout while Render wakes the container.")
            print("    2. Check the Render dashboard to confirm the database instance status is 'Available'.")
            print("    3. Ensure Render External Connection string (not internal private string) is being used.")
            print("    4. If Render IP access controls are enabled, verify that incoming connections are whitelisted.")

    print("\n" + "=" * 80)
    if results["step_6_select_1"] and results["step_9_tables_verified"]:
        print("[+] VERIFICATION STATUS: 100% HEALTHY - ALL CHECKS PASSED")
    else:
        print("[!] VERIFICATION STATUS: FAILED CHECKS DETECTED")
    print("=" * 80)

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Production PostgreSQL connection and SSL.")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL connection string override")
    args = parser.parse_args()
    res = run_verification(args.pg_url)
    if not (res["step_6_select_1"] and res["step_9_tables_verified"]):
        sys.exit(1)
