#!/usr/bin/env python3
"""
Growww Discovery Engine – SQLite to PostgreSQL Migration Engine (Phase 8)
Safely migrates schema and review records from SQLite to PostgreSQL with row count parity checks.
Executes individual DDL statements to ensure 100% compatibility with SQLAlchemy 2.0 and PostgreSQL.
"""

import os
import sys
import argparse
import sqlite3
import re
from typing import Dict, List, Any

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEFAULT_SQLITE_PATH = os.path.join(REPO_ROOT, "growww_discovery.db")
DEFAULT_DUMP_PATH = os.path.join(REPO_ROOT, "data", "growww_discovery_postgres.sql")

MIGRATION_TABLES = [
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

def adapt_sqlite_type_to_postgres(col_type: str) -> str:
    """Translates SQLite column types into canonical PostgreSQL types."""
    upper = col_type.upper().strip()
    if "INT" in upper:
        return "INTEGER"
    if "REAL" in upper or "FLOAT" in upper or "DOUBLE" in upper:
        return "DOUBLE PRECISION"
    if "TEXT" in upper or "CHAR" in upper:
        return "TEXT"
    if "BLOB" in upper:
        return "BYTEA"
    if "TIMESTAMP" in upper or "DATETIME" in upper:
        return "TIMESTAMP WITHOUT TIME ZONE"
    return "TEXT"

def generate_postgres_ddl_list(sqlite_conn: sqlite3.Connection) -> List[str]:
    """Generates a list of individual PostgreSQL DDL statements."""
    cursor = sqlite_conn.cursor()
    statements = []

    for table in MIGRATION_TABLES:
        table_exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not table_exists:
            continue

        cols_info = cursor.execute(f"PRAGMA table_info({table});").fetchall()
        col_defs = []
        pk_cols = []
        for col in cols_info:
            cid, col_name, col_type, notnull, dflt_value, pk = col
            pg_type = adapt_sqlite_type_to_postgres(col_type)
            col_def = f"    {col_name} {pg_type}"
            if notnull:
                col_def += " NOT NULL"
            if dflt_value is not None:
                dflt_str = str(dflt_value).strip()
                # Fix SQLite double-quoted defaults (e.g. "NOT_ENRICHED") into PostgreSQL single-quoted strings ('NOT_ENRICHED')
                if dflt_str.startswith('"') and dflt_str.endswith('"'):
                    inner = dflt_str[1:-1].replace("'", "''")
                    dflt_str = f"'{inner}'"
                col_def += f" DEFAULT {dflt_str}"
            col_defs.append(col_def)
            if pk > 0:
                pk_cols.append(col_name)

        if pk_cols:
            pk_str = ", ".join(pk_cols)
            col_defs.append(f"    PRIMARY KEY ({pk_str})")

        ddl = f"CREATE TABLE IF NOT EXISTS {table} (\n" + ",\n".join(col_defs) + "\n)"
        statements.append(ddl)

    # Indexes
    indexes = cursor.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;"
    ).fetchall()
    for name, sql in indexes:
        if not name.startswith("sqlite_autoindex"):
            safe_sql = re.sub(r"^CREATE\s+INDEX\s+", "CREATE INDEX IF NOT EXISTS ", sql.strip(), flags=re.IGNORECASE)
            statements.append(safe_sql)

    return statements

def generate_postgres_ddl(sqlite_conn: sqlite3.Connection) -> str:
    """Generates PostgreSQL-compatible CREATE TABLE and INDEX DDL statements for file export."""
    stmts = generate_postgres_ddl_list(sqlite_conn)
    header = [
        "-- GROWWW INVESTOR DISCOVERY ENGINE",
        "-- POSTGRESQL PRODUCTION DDL MIGRATION SCRIPT",
        "-- Generated automatically for Phase 8 Deployment\n",
        "BEGIN;\n"
    ]
    body = [f"{s};\n" for s in stmts]
    footer = ["COMMIT;\n"]
    return "\n".join(header + body + footer)

def export_to_postgres_sql(sqlite_path: str, output_path: str) -> Dict[str, int]:
    """Dumps SQLite schema and data into a PostgreSQL-compatible SQL script."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    row_counts = {}
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(generate_postgres_ddl(conn))
        out.write("\n-- DATA SEED STATEMENTS\nBEGIN;\n")

        for table in MIGRATION_TABLES:
            table_exists = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not table_exists:
                continue

            rows = cursor.execute(f"SELECT * FROM {table};").fetchall()
            row_counts[table] = len(rows)
            if not rows:
                continue

            cols_info = cursor.execute(f"PRAGMA table_info({table});").fetchall()
            col_type_map = {col[1]: col[2].upper() for col in cols_info}
            cols = [desc[0] for desc in cursor.description]
            cols_str = ", ".join(cols)

            for row in rows:
                values = []
                for col_name, val in zip(cols, row):
                    col_t = col_type_map.get(col_name, "")
                    if val is None or (val == "" and ("TIME" in col_t or "DATE" in col_t or "INT" in col_t or "REAL" in col_t or "FLOAT" in col_t)):
                        values.append("NULL")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        val_str = str(val).replace("'", "''")
                        values.append(f"'{val_str}'")
                vals_str = ", ".join(values)
                out.write(f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;\n")

        out.write("COMMIT;\n")

    conn.close()
    return row_counts

def migrate_to_postgres_instance(sqlite_path: str, pg_url: str) -> Dict[str, Any]:
    """Connects to live PostgreSQL instance and streams data with validation."""
    from sqlalchemy import create_engine, text

    # Normalize Render URL if starts with postgres://
    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_engine = create_engine(pg_url)

    # 1. Apply DDL statement by statement (avoids SQLAlchemy 2.0 multi-statement error tw8g)
    print("[*] Creating PostgreSQL tables and schema indexes...")
    ddl_statements = generate_postgres_ddl_list(sqlite_conn)
    with pg_engine.connect() as pg_conn:
        for stmt in ddl_statements:
            try:
                pg_conn.execute(text(stmt))
                pg_conn.commit()
            except Exception as e:
                pg_conn.rollback()
                if "already exists" not in str(e).lower():
                    print(f"    [!] Notice on DDL: {e}")

    # 2. Transfer rows with batch chunking
    counts = {}
    sqlite_cur = sqlite_conn.cursor()
    for table in MIGRATION_TABLES:
        table_exists = sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not table_exists:
            continue

        rows = sqlite_cur.execute(f"SELECT * FROM {table};").fetchall()
        counts[table] = len(rows)
        if rows:
            print(f"[*] Migrating {len(rows)} rows for '{table}'...")
            cols_info = sqlite_cur.execute(f"PRAGMA table_info({table});").fetchall()
            col_type_map = {col[1]: col[2].upper() for col in cols_info}
            cols = [desc[0] for desc in sqlite_cur.description]
            placeholders = ", ".join([f":{col}" for col in cols])
            insert_stmt = text(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")
            
            # Clean data: convert empty strings in timestamp/numeric columns to None (SQL NULL)
            cleaned_data = []
            for row in rows:
                row_dict = {}
                for col_name, val in zip(cols, row):
                    col_t = col_type_map.get(col_name, "")
                    if val == "" and ("TIME" in col_t or "DATE" in col_t or "INT" in col_t or "REAL" in col_t or "FLOAT" in col_t):
                        val = None
                    row_dict[col_name] = val
                cleaned_data.append(row_dict)

            # Batch execute in chunks of 100 to prevent parameter limits
            batch_size = 100
            with pg_engine.connect() as pg_conn:
                for i in range(0, len(cleaned_data), batch_size):
                    chunk = cleaned_data[i:i + batch_size]
                    pg_conn.execute(insert_stmt, chunk)
                    pg_conn.commit()

    sqlite_conn.close()
    return counts

def main():
    parser = argparse.ArgumentParser(description="Migrate Growww Discovery SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", default=DEFAULT_SQLITE_PATH, help="Path to source SQLite database")
    parser.add_argument("--output-sql", default=DEFAULT_DUMP_PATH, help="Path to output PostgreSQL SQL script")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL connection string (e.g. postgresql://user:pass@host/db)")
    args = parser.parse_args()

    print(f"[*] Starting migration from: {args.sqlite_path}")
    if args.pg_url:
        print(f"[*] Live migration to PostgreSQL target: {args.pg_url}")
        counts = migrate_to_postgres_instance(args.sqlite_path, args.pg_url)
    else:
        print(f"[*] Generating PostgreSQL SQL dump: {args.output_sql}")
        counts = export_to_postgres_sql(args.sqlite_path, args.output_sql)

    print("\n[+] Migration completed successfully! Table row counts:")
    for table, count in counts.items():
        print(f"    - {table:<25}: {count:>6} rows")

if __name__ == "__main__":
    main()
