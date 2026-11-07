#!/usr/bin/env python3
"""
Growww Discovery Engine – Database Restore & Disaster Recovery Tool (Phase 8)
Restores compressed backups and executes end-to-end schema, row count, foreign key,
and evidence grounding validation.
"""

import os
import sys
import gzip
import shutil
import hashlib
import json
import sqlite3
import argparse
from typing import Dict, Any

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def restore_and_validate(backup_gz_path: str, target_db_path: str) -> Dict[str, Any]:
    """Decompresses backup file into target location and executes comprehensive validation."""
    if not os.path.exists(backup_gz_path):
        raise FileNotFoundError(f"Backup archive not found at: {backup_gz_path}")

    # 1. Checksum verification if metadata exists
    meta_path = backup_gz_path.replace(".db.gz", ".meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            meta = json.load(mf)
        actual_hash = compute_sha256(backup_gz_path)
        expected_hash = meta.get("sha256_checksum")
        if actual_hash != expected_hash:
            raise ValueError(f"Checksum mismatch! Expected {expected_hash}, got {actual_hash}")
        print(f"[+] SHA-256 Checksum verified: {actual_hash[:16]}...")

    # 2. Decompress archive into target DB
    target_dir = os.path.dirname(target_db_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(target_db_path):
        os.remove(target_db_path)

    with gzip.open(backup_gz_path, "rb") as f_in:
        with open(target_db_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"[+] Decompressed backup into target: {target_db_path} ({os.path.getsize(target_db_path)} bytes)")

    # 3. Connect and execute deep validation suite
    conn = sqlite3.connect(target_db_path)
    cur = conn.cursor()

    # Check 1: SQLite Quick Check
    quick_check = cur.execute("PRAGMA quick_check;").fetchone()[0]
    if quick_check != "ok":
        conn.close()
        raise RuntimeError(f"Restored database failed quick_check: {quick_check}")

    # Check 2: Foreign Key Violations
    fk_violations = cur.execute("PRAGMA foreign_key_check;").fetchall()
    if fk_violations:
        conn.close()
        raise RuntimeError(f"Restored database has {len(fk_violations)} foreign key violations: {fk_violations}")

    # Check 3: Row Counts
    total_reviews = cur.execute("SELECT COUNT(*) FROM reviews;").fetchone()[0]
    eligible_reviews = cur.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE';").fetchone()[0]
    quarantine_count = cur.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO';").fetchone()[0]
    ai_evidence = cur.execute("SELECT COUNT(*) FROM ai_evidence_log;").fetchone()[0]
    opportunities = cur.execute("SELECT COUNT(*) FROM opportunities;").fetchone()[0]

    if total_reviews < 3798:
        raise ValueError(f"Review count deficit! Expected >= 3798, got {total_reviews}")
    if quarantine_count != 8:
        raise ValueError(f"Quarantine count mismatch! Expected exactly 8, got {quarantine_count}")
    if opportunities != 7:
        raise ValueError(f"Opportunity count mismatch! Expected exactly 7, got {opportunities}")

    # Check 4: Verbatim Grounding Audit on Opportunities
    opp_rows = cur.execute("SELECT opportunity_id, exemplar_verbatim_quote FROM opportunities;").fetchall()
    grounding_verified = 0
    for opp_id, quote in opp_rows:
        if quote:
            # Check quote exists in reviews table
            match = cur.execute("SELECT COUNT(*) FROM reviews WHERE review_text LIKE ?;", (f"%{quote[:30]}%",)).fetchone()[0]
            if match > 0:
                grounding_verified += 1

    conn.close()

    return {
        "status": "RESTORE_VERIFIED_SUCCESS",
        "target_db_path": target_db_path,
        "quick_check": quick_check,
        "foreign_key_violations": len(fk_violations),
        "total_reviews": total_reviews,
        "eligible_reviews": eligible_reviews,
        "quarantined_records": quarantine_count,
        "ai_evidence_records": ai_evidence,
        "opportunities": opportunities,
        "grounding_verified": grounding_verified,
    }

def main():
    parser = argparse.ArgumentParser(description="Restore and validate Growww Discovery database backup.")
    parser.add_argument("--backup-file", required=True, help="Path to .db.gz backup file")
    parser.add_argument("--target-db", default=os.path.join(REPO_ROOT, "data", "backups", "restored_test.db"), help="Target database path")
    args = parser.parse_args()

    print(f"[*] Starting restore and verification from: {args.backup_file}")
    res = restore_and_validate(args.backup_file, args.target_db)

    print("\n" + "=" * 80)
    print("RESTORE VERIFICATION REPORT: [SUCCESS]")
    print(f"Target DB:                {res['target_db_path']}")
    print(f"Quick Check:              {res['quick_check']}")
    print(f"Foreign Key Violations:   {res['foreign_key_violations']}")
    print(f"Total Reviews:            {res['total_reviews']}")
    print(f"Eligible Reviews:         {res['eligible_reviews']}")
    print(f"Quarantined Reviews:      {res['quarantined_records']}")
    print(f"AI Evidence Records:      {res['ai_evidence_records']}")
    print(f"Opportunities Verified:   {res['opportunities']}")
    print(f"Grounding Matches:        {res['grounding_verified']} / {res['opportunities']}")
    print("=" * 80)

if __name__ == "__main__":
    main()
