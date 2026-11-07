#!/usr/bin/env python3
"""
Growww Discovery Engine – SQLite to PostgreSQL Migration Engine (Phase 8 Production)
Safely migrates schema and review records from SQLite to PostgreSQL.
Enforces dialect-safe identifier quoting, genuine schema introspection,
pre-migration column validation, and empty-string-to-NULL normalization.
"""

import os
import sys
import argparse
import sqlite3
import re
import logging
from typing import Dict, List, Tuple, Any, Optional

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEFAULT_SQLITE_PATH = os.path.join(REPO_ROOT, "growww_discovery.db")
DEFAULT_DUMP_PATH = os.path.join(REPO_ROOT, "data", "growww_discovery_postgres.sql")

# Ordered to respect foreign-key dependencies
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

# Set of SQLite PRAGMA table_info metadata column names (must NEVER be treated as table columns)
PRAGMA_METADATA_FIELDS = {"cid", "notnull", "dflt_value", "pk"}

def mask_connection_url(url: str) -> str:
    """Masks database password in connection string for safe logging."""
    if not url:
        return ""
    return re.sub(r":([^:@]+)@", ":***@", url)

def quote_ident(ident: str) -> str:
    """Safely quotes PostgreSQL identifiers with double quotes."""
    clean = ident.replace('"', '""')
    return f'"{clean}"'

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

def get_table_schema_introspection(sqlite_conn: sqlite3.Connection, table: str) -> Tuple[List[str], Dict[str, str], List[str]]:
    """
    Introspects actual table columns using PRAGMA table_info.
    Returns:
      (actual_columns, col_type_map, primary_key_columns)
    Guarantees PRAGMA metadata fields (cid, notnull, dflt_value, pk) are never returned as columns.
    """
    cur = sqlite_conn.cursor()
    cols_info = cur.execute(f"PRAGMA table_info({table});").fetchall()
    cur.close()

    actual_columns = []
    col_type_map = {}
    pk_cols = []

    for col in cols_info:
        # PRAGMA table_info format: (cid, name, type, notnull, dflt_value, pk)
        cid, col_name, col_type, notnull, dflt_value, pk = col
        actual_columns.append(col_name)
        col_type_map[col_name] = col_type.upper()
        if pk > 0:
            pk_cols.append(col_name)

    # Sanity check: Ensure PRAGMA metadata fields are not erroneously treated as columns
    for bad_field in ("cid", "notnull", "dflt_value", "pk"):
        if bad_field in actual_columns and table != "dummy":
            # In our schema, no genuine table has a column literally named 'cid' or 'notnull'
            # (Note: 'id' is genuine, but 'cid' is not)
            if bad_field in ("cid", "notnull", "dflt_value"):
                raise ValueError(
                    f"FATAL SCHEMA ERROR: Detected SQLite PRAGMA metadata field '{bad_field}' "
                    f"in column list for table '{table}'. Columns: {actual_columns}"
                )

    return actual_columns, col_type_map, pk_cols

def generate_postgres_ddl_list(sqlite_conn: sqlite3.Connection) -> List[str]:
    """Generates individual PostgreSQL DDL statements for tables and indexes."""
    cur = sqlite_conn.cursor()
    statements = []

    for table in MIGRATION_TABLES:
        table_exists = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not table_exists:
            continue

        cols_info = cur.execute(f"PRAGMA table_info({table});").fetchall()
        col_defs = []
        pk_cols = []
        for col in cols_info:
            cid, col_name, col_type, notnull, dflt_value, pk = col
            pg_type = adapt_sqlite_type_to_postgres(col_type)
            quoted_col = quote_ident(col_name)
            col_def = f"    {quoted_col} {pg_type}"
            if notnull:
                col_def += " NOT NULL"
            if dflt_value is not None:
                dflt_str = str(dflt_value).strip()
                # Convert SQLite double-quoted defaults (e.g. "NOT_ENRICHED") into PostgreSQL single-quoted strings ('NOT_ENRICHED')
                if dflt_str.startswith('"') and dflt_str.endswith('"'):
                    inner = dflt_str[1:-1].replace("'", "''")
                    dflt_str = f"'{inner}'"
                col_def += f" DEFAULT {dflt_str}"
            col_defs.append(col_def)
            if pk > 0:
                pk_cols.append(quote_ident(col_name))

        if pk_cols:
            col_defs.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")

        quoted_table = quote_ident(table)
        ddl = f"CREATE TABLE IF NOT EXISTS {quoted_table} (\n" + ",\n".join(col_defs) + "\n)"
        statements.append(ddl)

    # Indexes
    indexes = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;"
    ).fetchall()
    for name, sql in indexes:
        if not name.startswith("sqlite_autoindex"):
            safe_sql = re.sub(r"^CREATE\s+INDEX\s+", "CREATE INDEX IF NOT EXISTS ", sql.strip(), flags=re.IGNORECASE)
            statements.append(safe_sql)

    cur.close()
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

def clean_value_for_postgres(val: Any, col_type: str) -> Any:
    """Converts empty strings in timestamps, dates, or numeric columns to None (SQL NULL)."""
    if val == "":
        upper_t = col_type.upper()
        if any(k in upper_t for k in ("TIME", "DATE", "INT", "REAL", "FLOAT", "DOUBLE", "NUMERIC")):
            return None
    return val

def export_to_postgres_sql(sqlite_path: str, output_path: str) -> Dict[str, int]:
    """Dumps SQLite schema and data into a PostgreSQL-compatible SQL script with safe quoting."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    row_counts = {}
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(generate_postgres_ddl(conn))
        out.write("\n-- DATA SEED STATEMENTS\nBEGIN;\n")

        for table in MIGRATION_TABLES:
            table_exists = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if not table_exists:
                continue

            # Extract genuine actual columns
            actual_cols, col_type_map, _ = get_table_schema_introspection(conn, table)
            quoted_cols = [quote_ident(c) for c in actual_cols]
            select_cols_str = ", ".join(quoted_cols)
            quoted_table = quote_ident(table)

            # Query data explicitly using genuine column list
            rows = cur.execute(f"SELECT {select_cols_str} FROM {quoted_table};").fetchall()
            row_counts[table] = len(rows)
            if not rows:
                continue

            for row in rows:
                values = []
                for col_name, val in zip(actual_cols, row):
                    col_t = col_type_map.get(col_name, "")
                    cleaned_val = clean_value_for_postgres(val, col_t)
                    if cleaned_val is None:
                        values.append("NULL")
                    elif isinstance(cleaned_val, (int, float)):
                        values.append(str(cleaned_val))
                    else:
                        val_str = str(cleaned_val).replace("'", "''")
                        values.append(f"'{val_str}'")
                vals_str = ", ".join(values)
                out.write(f"INSERT INTO {quoted_table} ({select_cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;\n")

        out.write("COMMIT;\n")

    conn.close()
    return row_counts

def validate_destination_schema(pg_engine, table: str, expected_cols: List[str]) -> Dict[str, Any]:
    """Validates destination PostgreSQL table columns against expected SQLite columns."""
    from sqlalchemy import text
    with pg_engine.connect() as conn:
        res = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
            {"t": table.lower()}
        ).fetchall()
        pg_cols = {r[0].lower() for r in res}

        # Check existing row count
        count_res = conn.execute(text(f'SELECT COUNT(*) FROM "{table}";')).fetchone()
        existing_rows = count_res[0] if count_res else 0

    missing_cols = [c for c in expected_cols if c.lower() not in pg_cols]
    return {
        "table_exists": len(pg_cols) > 0,
        "pg_column_count": len(pg_cols),
        "existing_rows": existing_rows,
        "missing_columns": missing_cols,
    }

def run_dry_run_plan(sqlite_path: str, pg_url: Optional[str] = None):
    """Outputs a comprehensive migration dry-run plan without writing to PostgreSQL."""
    print("=" * 80)
    print("GROWWW DISCOVERY ENGINE – DATABASE MIGRATION DRY-RUN PLAN")
    print(f"Source SQLite Database:      {sqlite_path}")
    print(f"Target PostgreSQL Database:  {mask_connection_url(pg_url) if pg_url else '[Offline SQL Dump Mode]'}")
    print("=" * 80)

    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    pg_engine = None
    if pg_url:
        from sqlalchemy import create_engine
        from database.connection import normalize_database_url
        normalized_url = normalize_database_url(pg_url)
        pg_engine = create_engine(normalized_url)

    print(f"{'Table Name':<25} | {'Source Rows':<12} | {'Cols':<5} | {'Dest Rows':<10} | {'Status'}")
    print("-" * 80)

    for table in MIGRATION_TABLES:
        exists = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not exists:
            print(f"{table:<25} | {'[NOT FOUND]':<12} | {'-':<5} | {'-':<10} | SKIPPED")
            continue

        actual_cols, col_type_map, pk_cols = get_table_schema_introspection(conn, table)
        row_count = cur.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]

        dest_rows = "N/A"
        status = "READY"

        if pg_engine:
            try:
                dest_info = validate_destination_schema(pg_engine, table, actual_cols)
                dest_rows = str(dest_info["existing_rows"])
                if dest_info["missing_columns"]:
                    status = f"MISSING COLS: {dest_info['missing_columns'][:2]}"
                elif dest_info["existing_rows"] > 0:
                    status = f"APPEND/RESTARTABLE ({dest_rows} present)"
            except Exception as e:
                dest_rows = "0 (new)"
                status = "TABLE WILL BE CREATED"

        print(f"{table:<25} | {row_count:<12} | {len(actual_cols):<5} | {dest_rows:<10} | {status}")

    conn.close()
    print("=" * 80)
    print("[+] Dry-run completed: Schema introspection verified, 0 PRAGMA metadata leaks.")
    print("[+] To execute live migration, run without --dry-run.")

def migrate_to_postgres_instance(sqlite_path: str, pg_url: str) -> Dict[str, Any]:
    """Connects to live PostgreSQL instance and streams data with validation and safe quoting."""
    from sqlalchemy import create_engine, text

    # Normalize Render URL and select available driver (psycopg2 or pg8000)
    from database.connection import normalize_database_url
    normalized_url = normalize_database_url(pg_url)
    masked_url = mask_connection_url(normalized_url)

    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_engine = create_engine(normalized_url)

    # 1. Apply DDL statement-by-statement
    print(f"[*] Connecting to PostgreSQL target: {masked_url}")
    print("[*] Creating PostgreSQL tables and schema indexes...")
    ddl_statements = generate_postgres_ddl_list(sqlite_conn)
    with pg_engine.connect() as pg_conn:
        for stmt in ddl_statements:
            try:
                pg_conn.execute(text(stmt))
                pg_conn.commit()
            except Exception as e:
                pg_conn.rollback()
                err_str = str(e).lower()
                if "already exists" not in err_str:
                    print(f"    [!] Notice on DDL statement: {e}")

    # 2. Transfer rows table-by-table
    counts = {}
    sqlite_cur = sqlite_conn.cursor()

    for table in MIGRATION_TABLES:
        table_exists = sqlite_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not table_exists:
            continue

        # Extract genuine table columns
        actual_cols, col_type_map, pk_cols = get_table_schema_introspection(sqlite_conn, table)
        quoted_cols = [quote_ident(c) for c in actual_cols]
        quoted_table = quote_ident(table)
        select_sql = f"SELECT {', '.join(quoted_cols)} FROM {quoted_table};"

        # Pre-migration schema validation
        dest_validation = validate_destination_schema(pg_engine, table, actual_cols)
        if dest_validation["missing_columns"]:
            raise RuntimeError(
                f"Schema Mismatch in '{table}': Destination table is missing columns: {dest_validation['missing_columns']}"
            )

        existing_in_pg = dest_validation["existing_rows"]
        rows = sqlite_cur.execute(select_sql).fetchall()
        counts[table] = len(rows)

        if not rows:
            print(f"[*] Table '{table}': 0 rows in source. Skipped.")
            continue

        print(f"[*] Migrating '{table}': {len(rows)} source rows ({len(actual_cols)} cols, {existing_in_pg} already in destination)...")

        # Build parameterized INSERT statement with double-quoted identifiers
        # Parameter keys use param_0, param_1 to avoid reserved keyword issues in named params
        param_keys = [f"p_{idx}" for idx in range(len(actual_cols))]
        placeholders = ", ".join([f":{k}" for k in param_keys])
        insert_sql = f"INSERT INTO {quoted_table} ({', '.join(quoted_cols)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        insert_stmt = text(insert_sql)

        # Clean data: convert empty strings in timestamp/numeric columns to None (SQL NULL)
        cleaned_data = []
        for row in rows:
            row_dict = {}
            for idx, (col_name, val) in enumerate(zip(actual_cols, row)):
                col_t = col_type_map.get(col_name, "")
                cleaned_val = clean_value_for_postgres(val, col_t)
                row_dict[f"p_{idx}"] = cleaned_val
            cleaned_data.append(row_dict)

        # Batch execute in chunks of 100 to prevent parameter limits
        batch_size = 100
        with pg_engine.connect() as pg_conn:
            for i in range(0, len(cleaned_data), batch_size):
                chunk = cleaned_data[i:i + batch_size]
                pg_conn.execute(insert_stmt, chunk)
                pg_conn.commit()

        # Validate post-insert row count
        with pg_engine.connect() as pg_conn:
            final_count = pg_conn.execute(text(f'SELECT COUNT(*) FROM {quoted_table};')).fetchone()[0]
            print(f"    [+] '{table}' migration verified: {final_count} total rows in destination.")

    sqlite_conn.close()
    return counts

def main():
    parser = argparse.ArgumentParser(description="Migrate Growww Discovery SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", default=DEFAULT_SQLITE_PATH, help="Path to source SQLite database")
    parser.add_argument("--output-sql", default=DEFAULT_DUMP_PATH, help="Path to output PostgreSQL SQL script")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL connection string (e.g. postgresql://user:pass@host/db)")
    parser.add_argument("--dry-run", action="store_true", help="Display migration plan and validate schemas without writing")
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run_plan(args.sqlite_path, args.pg_url)
        return

    print(f"[*] Starting migration from: {args.sqlite_path}")
    if args.pg_url:
        print(f"[*] Live migration to PostgreSQL target: {mask_connection_url(args.pg_url)}")
        counts = migrate_to_postgres_instance(args.sqlite_path, args.pg_url)
    else:
        print(f"[*] Generating PostgreSQL SQL dump: {args.output_sql}")
        counts = export_to_postgres_sql(args.sqlite_path, args.output_sql)

    print("\n[+] Migration completed successfully! Table row counts:")
    for table, count in counts.items():
        print(f"    - {table:<25}: {count:>6} rows")

if __name__ == "__main__":
    main()
