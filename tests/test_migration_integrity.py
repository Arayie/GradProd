"""
Migration Integrity and Schema Introspection Regression Tests (Phase 8)
Verifies that SQLite PRAGMA table_info metadata fields (cid, notnull, dflt_value, pk)
are never treated as application columns, and that dialect-safe quoting and NULL conversions work.
"""

import os
import sys
import sqlite3
import pytest

# Ensure local lib/ in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.migrate_sqlite_to_postgres import (
    get_table_schema_introspection,
    clean_value_for_postgres,
    generate_postgres_ddl_list,
    MIGRATION_TABLES,
    DEFAULT_SQLITE_PATH,
    quote_ident,
)

@pytest.fixture
def sqlite_conn():
    conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
    yield conn
    conn.close()

def test_apps_table_schema_introspection(sqlite_conn):
    """
    Regression Test for Task:
    Ensure PRAGMA metadata fields (cid, notnull, dflt_value, pk) are NEVER returned
    as columns for the 'apps' table.
    """
    actual_cols, col_type_map, pk_cols = get_table_schema_introspection(sqlite_conn, "apps")
    
    # 1. Must have exactly 13 genuine columns
    assert len(actual_cols) == 13
    expected_apps_cols = [
        "id", "internal_app_id", "app_name", "developer_name", "apple_app_id",
        "google_play_package", "apple_listing_url", "google_play_listing_url",
        "storefront", "app_role", "verification_status", "created_at", "updated_at"
    ]
    assert actual_cols == expected_apps_cols

    # 2. PRAGMA metadata fields MUST NOT be present
    for bad in ("cid", "notnull", "dflt_value", "pk"):
        assert bad not in actual_cols, f"PRAGMA metadata field '{bad}' leaked into apps columns!"

    # 3. Primary key must be 'id'
    assert pk_cols == ["id"]

def test_all_migration_tables_schema_introspection(sqlite_conn):
    """Verifies that none of the 11 migration tables leak PRAGMA metadata fields."""
    for table in MIGRATION_TABLES:
        actual_cols, col_type_map, pk_cols = get_table_schema_introspection(sqlite_conn, table)
        assert len(actual_cols) > 0
        for bad in ("cid", "notnull", "dflt_value"):
            assert bad not in actual_cols, f"PRAGMA metadata field '{bad}' leaked into '{table}'!"

def test_quote_ident():
    """Verifies safe double-quoting of PostgreSQL identifiers."""
    assert quote_ident("apps") == '"apps"'
    assert quote_ident("order") == '"order"'
    assert quote_ident('col"name') == '"col""name"'

def test_clean_value_for_postgres():
    """Verifies empty strings in timestamps and numerics are converted to None (SQL NULL)."""
    assert clean_value_for_postgres("", "TIMESTAMP WITHOUT TIME ZONE") is None
    assert clean_value_for_postgres("", "DATE") is None
    assert clean_value_for_postgres("", "INTEGER") is None
    assert clean_value_for_postgres("", "DOUBLE PRECISION") is None
    assert clean_value_for_postgres("", "TEXT") == ""  # Text empty string preserved
    assert clean_value_for_postgres("2026-11-07 10:00:00", "TIMESTAMP") == "2026-11-07 10:00:00"
    assert clean_value_for_postgres(None, "TIMESTAMP") is None

def test_generate_postgres_ddl_list(sqlite_conn):
    """Verifies that generated DDL contains quoted identifiers and valid defaults."""
    stmts = generate_postgres_ddl_list(sqlite_conn)
    assert len(stmts) >= 30  # 11 tables + indexes

    # Verify apps table DDL
    apps_ddl = next(s for s in stmts if 'CREATE TABLE IF NOT EXISTS "apps"' in s)
    assert '"internal_app_id" TEXT NOT NULL' in apps_ddl
    assert '"cid"' not in apps_ddl
    assert '"notnull"' not in apps_ddl
    assert 'PRIMARY KEY ("id")' in apps_ddl

    # Verify reviews table DDL has single-quoted string defaults
    reviews_ddl = next(s for s in stmts if 'CREATE TABLE IF NOT EXISTS "reviews"' in s)
    assert "DEFAULT 'NOT_ENRICHED'" in reviews_ddl
    assert 'DEFAULT "NOT_ENRICHED"' not in reviews_ddl
    assert "DEFAULT 'PENDING'" in reviews_ddl
