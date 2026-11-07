#!/usr/bin/env python3
"""
Growww Discovery Engine – Database Backup Automation (Phase 8)
Creates atomic, compressed, timestamped database backups with SHA-256 checksums and retention enforcement.
"""

import os
import sys
import gzip
import shutil
import hashlib
import json
import sqlite3
import argparse
from datetime import datetime
from typing import Dict, Any

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEFAULT_DB_PATH = os.path.join(REPO_ROOT, "growww_discovery.db")
DEFAULT_BACKUP_DIR = os.path.join(REPO_ROOT, "data", "backups")

def compute_sha256(file_path: str) -> str:
    """Calculates SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def create_sqlite_backup(source_db_path: str, backup_dir: str) -> Dict[str, Any]:
    """Uses SQLite native backup API to create an atomic, non-locking, compressed snapshot."""
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    temp_snapshot_path = os.path.join(backup_dir, f"snapshot_{timestamp}.db")
    compressed_backup_path = os.path.join(backup_dir, f"growww_backup_{timestamp}.db.gz")
    metadata_path = os.path.join(backup_dir, f"growww_backup_{timestamp}.meta.json")

    # 1. Atomic online backup via SQLite API
    source_conn = sqlite3.connect(source_db_path)
    dest_conn = sqlite3.connect(temp_snapshot_path)
    with dest_conn:
        source_conn.backup(dest_conn, pages=250)
    dest_conn.close()
    source_conn.close()

    # 2. Verify snapshot integrity before compression
    verify_conn = sqlite3.connect(temp_snapshot_path)
    cur = verify_conn.cursor()
    quick_check = cur.execute("PRAGMA quick_check;").fetchone()[0]
    if quick_check != "ok":
        verify_conn.close()
        os.remove(temp_snapshot_path)
        raise RuntimeError(f"Snapshot integrity verification failed: {quick_check}")

    row_metrics = {
        "total_reviews": cur.execute("SELECT COUNT(*) FROM reviews;").fetchone()[0],
        "eligible_reviews": cur.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE';").fetchone()[0],
        "quarantined_records": cur.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO';").fetchone()[0],
        "ai_evidence_records": cur.execute("SELECT COUNT(*) FROM ai_evidence_log;").fetchone()[0],
        "opportunities": cur.execute("SELECT COUNT(*) FROM opportunities;").fetchone()[0],
    }
    verify_conn.close()

    # 3. Compress snapshot with gzip
    with open(temp_snapshot_path, "rb") as f_in:
        with gzip.open(compressed_backup_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Remove uncompressed temp snapshot
    os.remove(temp_snapshot_path)

    # 4. Generate SHA-256 and metadata manifest
    sha256_hash = compute_sha256(compressed_backup_path)
    backup_size = os.path.getsize(compressed_backup_path)

    metadata = {
        "timestamp_utc": timestamp,
        "backup_filename": os.path.basename(compressed_backup_path),
        "backup_path": compressed_backup_path,
        "file_size_bytes": backup_size,
        "sha256_checksum": sha256_hash,
        "engine": "SQLite 3.35+ (WAL)",
        "source_db": source_db_path,
        "metrics": row_metrics,
        "status": "VERIFIED_VALID",
    }

    with open(metadata_path, "w", encoding="utf-8") as meta_file:
        json.dump(metadata, meta_file, indent=2)

    return metadata

def enforce_retention_policy(backup_dir: str, max_backups: int = 28):
    """Enforces retention window by removing oldest backups exceeding limit."""
    gz_files = sorted(
        [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".db.gz")],
        key=os.path.getmtime
    )
    if len(gz_files) > max_backups:
        excess = len(gz_files) - max_backups
        for f in gz_files[:excess]:
            try:
                os.remove(f)
                meta_file = f.replace(".db.gz", ".meta.json")
                if os.path.exists(meta_file):
                    os.remove(meta_file)
            except Exception as e:
                print(f"Warning: Failed to prune old backup {f}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create Growww Discovery Engine database backup.")
    parser.add_argument("--source-db", default=DEFAULT_DB_PATH, help="Path to database file")
    parser.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR, help="Destination directory for backups")
    parser.add_argument("--retention", type=int, default=28, help="Maximum number of backups to retain")
    args = parser.parse_args()

    print(f"[*] Starting backup of: {args.source_db}")
    meta = create_sqlite_backup(args.source_db, args.backup_dir)
    enforce_retention_policy(args.backup_dir, args.retention)

    print("\n[+] BACKUP COMPLETED & VERIFIED SUCCESSFULLY!")
    print(f"    File:      {meta['backup_filename']} ({meta['file_size_bytes']} bytes)")
    print(f"    SHA-256:   {meta['sha256_checksum']}")
    print(f"    Reviews:   {meta['metrics']['total_reviews']} total ({meta['metrics']['eligible_reviews']} eligible, {meta['metrics']['quarantined_records']} quarantined)")
    print(f"    AI Ev:     {meta['metrics']['ai_evidence_records']}")
    print(f"    Opps:      {meta['metrics']['opportunities']}")

if __name__ == "__main__":
    main()
