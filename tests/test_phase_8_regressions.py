"""
Regression Test Suite for Phase 8 Production Deployment & Cloud Handover
Validates fixes for:
- Issue 1: Explicit psycopg2 driver dialect normalization
- Issue 2: DatabaseManager get_connection contract across UI pages
- Issue 3: Zero silent SQLite fallback in production mode
- Issue 4: Package init files and unambiguous imports
- Issue 5: PostgreSQL-compatible schema initialization
- Issue 6: All 16 Streamlit UI pages render cleanly
"""

import os
import sys
import pytest
import warnings
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from database.connection import (
    DatabaseConnection,
    normalize_database_url,
    mask_connection_url,
    ManagedConnectionContext,
    DictRow,
    get_db,
)
from core.database_manager import DatabaseManager, get_database_manager
from core.auth import AuthService


def test_regression_issue_1_explicit_psycopg2_driver():
    """Verify normalize_database_url explicitly uses postgresql+psycopg2:// dialect."""
    url1 = "postgres://growww_user:secret@render.com/growww_discovery"
    norm1 = normalize_database_url(url1)
    assert norm1.startswith("postgresql+psycopg2://")
    assert "secret" in norm1

    url2 = "postgresql://growww_user:secret@render.com/growww_discovery"
    norm2 = normalize_database_url(url2)
    assert norm2.startswith("postgresql+psycopg2://")

    # Already qualified URLs have sslmode=require enforced
    url3 = "postgresql+psycopg2://user:pass@host/db"
    assert normalize_database_url(url3) == "postgresql+psycopg2://user:pass@host/db?sslmode=require"

    # URL with existing sslmode is normalized to require
    url4 = "postgresql://user:pass@host/db?sslmode=disable"
    assert "sslmode=require" in normalize_database_url(url4)
    assert "sslmode=disable" not in normalize_database_url(url4)

    # Masking test
    masked = mask_connection_url(norm1)
    assert "secret" not in masked
    assert "****" in masked


def test_regression_issue_2_database_manager_contract():
    """Verify DatabaseManager exposes get_connection() and get_cursor() with full lifecycle."""
    db_mgr = get_database_manager()
    assert hasattr(db_mgr, "get_connection")
    assert hasattr(db_mgr, "get_cursor")

    # Test context manager pattern
    with db_mgr.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 AS num;")
        row = cur.fetchone()
        assert row[0] == 1
        assert row["num"] == 1

    # Test direct call pattern
    conn = db_mgr.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 2 AS num;")
    assert cur.fetchone()[0] == 2
    conn.close()


def test_regression_issue_3_no_silent_sqlite_fallback():
    """Verify production PostgreSQL failure raises an error and NEVER silently falls back to SQLite."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://invalid_user:invalid_pass@invalid_host:5432/bad_db"}):
        db = DatabaseConnection()
        assert db.is_postgres is True
        with pytest.raises(RuntimeError) as exc_info:
            db.get_raw_connection()
        assert "Production PostgreSQL database connection" in str(exc_info.value)
        # Verify db was NOT silently switched to SQLite
        assert db.is_postgres is True


def test_regression_issue_4_package_initialization():
    """Verify all project modules have __init__.py and import cleanly without KeyError."""
    packages = ["database", "core", "ui", "ui/pages", "ingestion", "services", "validation"]
    for pkg in packages:
        init_file = os.path.join(REPO_ROOT, pkg, "__init__.py")
        assert os.path.exists(init_file), f"Missing __init__.py in {pkg}"

    import database.connection
    import core.database_manager
    assert "database.connection" in sys.modules
    assert "core.database_manager" in sys.modules


def test_regression_issue_5_postgres_schema_initialization_safety():
    """Verify PostgreSQL schema initialization checks existence, handles missing files, and propagates errors."""
    # Case A: Table already exists (idempotent, no DDL executed)
    db_a = DatabaseConnection()
    db_a.is_postgres = True
    db_a.raw_url = "postgresql://user:pass@host/db"

    with patch.object(db_a, "verify_connection") as mock_verify:
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = "public.reviews"
        db_a._engine = mock_engine

        db_a.initialize_schema()
        assert mock_verify.called
        assert mock_conn.execute.called

    # Case B: Table does not exist (empty database, executes DDL from postgres_schema.sql)
    db_b = DatabaseConnection()
    db_b.is_postgres = True
    db_b.raw_url = "postgresql://user:pass@host/db"

    with patch.object(db_b, "verify_connection") as mock_verify:
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = None  # Not existing
        db_b._engine = mock_engine

        db_b.initialize_schema()
        assert mock_verify.called
        # Verify statements were executed
        assert mock_conn.execute.call_count > 1

    # Case C: Missing schema file raises FileNotFoundError
    db_c = DatabaseConnection()
    db_c.is_postgres = True
    with pytest.raises(FileNotFoundError):
        db_c._initialize_postgres_schema(schema_file="/nonexistent/path/postgres_schema.sql")

    # Case D: Database connection failure propagates RuntimeError without SQLite fallback
    db_d = DatabaseConnection()
    db_d.is_postgres = True
    db_d.raw_url = "postgresql://user:pass@host/db"
    with patch.object(db_d, "verify_connection", side_effect=Exception("Connection timed out")):
        with pytest.raises(RuntimeError) as exc_info:
            db_d.initialize_schema()
        assert "PostgreSQL schema initialization failed" in str(exc_info.value)
        assert db_d.is_postgres is True


def test_regression_issue_6_all_16_pages_render_cleanly():
    """Audit and verify that all 16 Streamlit UI pages render without exception."""
    warnings.filterwarnings("ignore")
    AuthService.init_session()
    AuthService.authenticate("admin", "Admin@Growww2026!")

    from ui.pages import (
        executive_overview,
        source_manager_ui,
        collection_history_ui,
        review_explorer_ui,
        sip_quality,
        sip_journey_explorer,
        investor_behaviour,
        theme_explorer,
        app_comparison,
        opportunity_radar,
        opportunity_detail,
        retention_model_ui,
        ai_evidence_log_ui,
        model_validation_ui,
        human_validation_ui,
        exports_reports,
    )

    all_pages = [
        executive_overview,
        source_manager_ui,
        collection_history_ui,
        review_explorer_ui,
        sip_quality,
        sip_journey_explorer,
        investor_behaviour,
        theme_explorer,
        app_comparison,
        opportunity_radar,
        opportunity_detail,
        retention_model_ui,
        ai_evidence_log_ui,
        model_validation_ui,
        human_validation_ui,
        exports_reports,
    ]

    for page in all_pages:
        page.render()


def test_regression_issue_7_analytics_independent_imports():
    """Verify that all analytics submodules can be imported independently without eager circular evaluation."""
    import analytics.benchmarking
    import analytics.lifecycle_analytics
    import analytics.opportunity_scoring
    import analytics.retention_modeling
    import analytics.theme_frequency
    import core.database_manager

    assert hasattr(analytics.benchmarking, "CrossAppBenchmarkEngine")
    assert hasattr(analytics.lifecycle_analytics, "LifecycleAnalyticsEngine")
    assert hasattr(analytics.opportunity_scoring, "OpportunityScoringEngine")
    assert hasattr(analytics.retention_modeling, "RetentionHypothesisEngine")
    assert hasattr(analytics.theme_frequency, "ThemeFrequencyEngine")


def test_regression_issue_8_ssl_pool_and_retry_lifecycle():
    """Verify SQLAlchemy engine pool parameters, sslmode=require, secrets handling, and bounded retries."""
    from database.connection import get_env_database_url

    # 1. Test get_env_database_url with os.environ
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test_user:pass@host/db"}):
        assert get_env_database_url() == "postgresql://test_user:pass@host/db"

    # 2. Test get_env_database_url with Streamlit secrets fallback
    with patch.dict(os.environ, {"DATABASE_URL": ""}):
        mock_st = MagicMock()
        mock_st.secrets = {"DATABASE_URL": "postgresql://secret_user:pass@render/db"}
        with patch.dict(sys.modules, {"streamlit": mock_st}):
            assert get_env_database_url() == "postgresql://secret_user:pass@render/db"

    # 3. Test get_env_database_url with nested Streamlit secrets
    with patch.dict(os.environ, {"DATABASE_URL": ""}):
        mock_st = MagicMock()
        mock_st.secrets = {
            "postgres": {
                "user": "pg_user",
                "password": "pg_pass",
                "host": "dpg-123.render.com",
                "port": 5432,
                "dbname": "growww_discovery"
            }
        }
        with patch.dict(sys.modules, {"streamlit": mock_st}):
            constructed = get_env_database_url()
            assert "pg_user:pg_pass@dpg-123.render.com:5432/growww_discovery" in constructed
            assert "sslmode=require" in constructed

    # 4. Test engine pooling parameters
    db = DatabaseConnection(db_path="postgresql://user:pass@host:5432/testdb")
    with patch("sqlalchemy.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        engine = db.get_engine()
        assert engine is mock_engine
        assert mock_create_engine.called
        kwargs = mock_create_engine.call_args[1]
        assert kwargs.get("pool_pre_ping") is True
        assert kwargs.get("pool_size") == 5
        assert kwargs.get("max_overflow") == 10
        assert kwargs.get("pool_recycle") == 300
        assert kwargs.get("pool_timeout") == 20
        connect_args = kwargs.get("connect_args", {})
        assert connect_args.get("sslmode") == "require"
        assert connect_args.get("connect_timeout") == 15
        assert connect_args.get("keepalives") == 1

    # 5. Test verify_connection retries on transient errors and fails fast on auth errors
    db_retry = DatabaseConnection(db_path="postgresql://user:pass@host:5432/testdb")
    mock_eng = MagicMock()
    # First attempt raises SSL closed, second attempt succeeds
    mock_conn = MagicMock()
    mock_conn.execute.return_value.scalar.side_effect = [1, "testdb", "user"]
    mock_eng.connect.side_effect = [
        Exception("SSL connection has been closed unexpectedly"),
        mock_conn
    ]
    mock_conn.__enter__.return_value = mock_conn
    db_retry._engine = mock_eng

    with patch("time.sleep"):
        res = db_retry.verify_connection(max_retries=3, retry_delay=0.01)
        assert res["verified"] is True
        assert res["database"] == "testdb"

    # Test fast failure on authentication error
    db_auth = DatabaseConnection(db_path="postgresql://user:wrong_pass@host:5432/testdb")
    mock_eng_auth = MagicMock()
    mock_eng_auth.connect.side_effect = Exception("password authentication failed for user")
    db_auth._engine = mock_eng_auth
    with pytest.raises(RuntimeError) as exc_info:
        db_auth.verify_connection(max_retries=3, retry_delay=0.01)
    assert "Database authentication failed" in str(exc_info.value)
    assert mock_eng_auth.connect.call_count == 1  # Fast-failed without retries


def test_regression_issue_9_data_cleaning_timestamp_nullification():
    """Verify that clean_value_for_postgres converts empty strings to None for timestamp/numeric columns."""
    from scripts.migrate_sqlite_to_postgres import clean_value_for_postgres

    # Timestamp column with empty string -> converted to None (SQL NULL)
    assert clean_value_for_postgres("", "review_created_at", "TIMESTAMP") is None
    assert clean_value_for_postgres("   ", "retrieved_at", "TIMESTAMP") is None
    assert clean_value_for_postgres("", "pii_processed_at", "TEXT") is None  # Caught by column name
    assert clean_value_for_postgres("", "latency_ms", "INTEGER") is None

    # Valid values are preserved
    assert clean_value_for_postgres("2026-11-06 17:00:00", "review_created_at", "TIMESTAMP") == "2026-11-06 17:00:00"
    assert clean_value_for_postgres(100, "token_count_input", "INTEGER") == 100
    assert clean_value_for_postgres(0.95, "confidence_score", "REAL") == 0.95

    # Text columns that legitimately allow empty string are preserved
    assert clean_value_for_postgres("", "source_description", "TEXT") == ""


