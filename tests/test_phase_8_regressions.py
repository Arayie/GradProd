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
    """Verify PostgreSQL schema initialization checks all tables, handles missing files, and propagates errors."""
    required_tables = [
        "apps", "source_routes", "import_batches", "ingestion_runs", "collection_errors",
        "collection_checkpoints", "reviews", "ai_evidence_log", "human_adjudications",
        "opportunities", "opportunity_audits"
    ]
    # Case A: All 11 tables already exist (idempotent, no DDL executed)
    db_a = DatabaseConnection()
    db_a.is_postgres = True
    db_a.raw_url = "postgresql://user:pass@host/db"

    with patch.object(db_a, "verify_connection") as mock_verify:
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        # Return all 11 table names
        mock_conn.execute.return_value.fetchall.return_value = [(t,) for t in [
            "apps", "source_routes", "import_batches", "ingestion_runs", "collection_errors",
            "collection_checkpoints", "reviews", "ai_evidence_log", "human_adjudications",
            "opportunities", "opportunity_audits"
        ]]
        db_a._engine = mock_engine

        db_a.initialize_schema()
        assert mock_verify.called
        assert mock_conn.execute.called

    # Case B: Tables do not exist (empty database, executes DDL via engine.begin())
    db_b = DatabaseConnection()
    db_b.is_postgres = True
    db_b.raw_url = "postgresql://user:pass@host/db"

    with patch.object(db_b, "verify_connection") as mock_verify:
        mock_engine = MagicMock()
        mock_check_conn = MagicMock()
        mock_ddl_conn = MagicMock()
        mock_verify_conn = MagicMock()

        # Connect returns empty initially, then all tables post-DDL
        mock_check_conn.execute.return_value.fetchall.return_value = []
        mock_verify_conn.execute.return_value.fetchall.return_value = [(t,) for t in [
            "apps", "source_routes", "import_batches", "ingestion_runs", "collection_errors",
            "collection_checkpoints", "reviews", "ai_evidence_log", "human_adjudications",
            "opportunities", "opportunity_audits"
        ]]
        mock_engine.connect.return_value.__enter__.side_effect = [mock_check_conn, mock_verify_conn]
        mock_engine.begin.return_value.__enter__.return_value = mock_ddl_conn
        db_b._engine = mock_engine

        db_b.initialize_schema()
        assert mock_verify.called
        assert mock_engine.begin.called
        assert mock_ddl_conn.execute.call_count > 1

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


def test_regression_issue_10_safe_diagnostics():
    """Verify safe diagnostics report host, db, driver, sslmode, source without exposing credentials."""
    from database.connection import get_connection_diagnostics

    pg_url = "postgresql://my_secret_user:super_secret_password@dpg-dbnlt0bbc2fs73fgp3g0-a.singapore-postgres.render.com:5432/growww_discovery?sslmode=require"
    diag = get_connection_diagnostics(pg_url, "streamlit_secrets")

    assert diag["hostname"] == "dpg-dbnlt0bbc2fs73fgp3g0-a.singapore-postgres.render.com"
    assert diag["port"] == 5432
    assert diag["database"] == "growww_discovery"
    assert diag["driver"] == "postgresql+psycopg2"
    assert diag["sslmode"] == "require"
    assert diag["source"] == "streamlit_secrets"

    # Confirm sensitive credentials are NOT anywhere in the diagnostic output
    diag_str = str(diag)
    assert "super_secret_password" not in diag_str
    assert "my_secret_user" not in diag_str


def test_regression_issue_11_production_enforcement():
    """Verify missing DATABASE_URL in production raises a clear configuration error without SQLite fallback."""
    from database.connection import is_production_environment

    # In production without PostgreSQL DATABASE_URL -> raises RuntimeError
    with patch("database.connection.is_production_environment", return_value=True):
        with patch("database.connection.get_env_database_url_with_source", return_value=("", "none")):
            with pytest.raises(RuntimeError) as exc_info:
                DatabaseConnection()
            assert "Production environment detected" in str(exc_info.value)
            assert "cannot run on SQLite" in str(exc_info.value)

    # In local development without PostgreSQL -> smoothly falls back to SQLite
    with patch("database.connection.is_production_environment", return_value=False):
        with patch("database.connection.get_env_database_url_with_source", return_value=("", "none")):
            db_dev = DatabaseConnection()
            assert db_dev.is_postgres is False
            assert "growww_discovery.db" in db_dev.db_path


def test_regression_issue_12_on_conflict_upsert_idempotency(tmp_path):
    """
    Verify AppRepository, SourceRouteRepository, and CheckpointRepository
    UPSERT statements work with ON CONFLICT and remain 100% idempotent
    without creating duplicate records.
    """
    from database.repositories import AppRepository, SourceRouteRepository, CheckpointRepository
    db_file = str(tmp_path / "test_upsert.db")
    db = DatabaseConnection(db_path=db_file)
    db.initialize_schema()

    app_repo = AppRepository(db)
    source_repo = SourceRouteRepository(db)
    ckpt_repo = CheckpointRepository(db)

    # 1. First synchronization of apps
    sample_apps = [
        {
            "internal_id": "groww",
            "official_name": "Groww: Stocks & Mutual Funds",
            "developer_name": "Groww Inc",
            "apple_app_store": {"app_id": "1404871703"},
            "google_play_store": {"package_name": "com.nextbillion.groww"},
            "app_role": "PRIMARY_TARGET",
            "verification_status": "VERIFIED",
        },
        {
            "internal_id": "zerodha_coin",
            "official_name": "Coin by Zerodha",
            "developer_name": "Zerodha",
            "apple_app_store": {"app_id": "1392892554"},
            "google_play_store": {"package_name": "com.zerodha.coin"},
            "app_role": "PEER_BENCHMARK",
            "verification_status": "VERIFIED",
        }
    ]
    app_repo.sync_from_config(sample_apps)
    assert app_repo.count() == 2

    # 2. Repeated synchronization: must be strictly idempotent (count stays 2)
    app_repo.sync_from_config(sample_apps)
    assert app_repo.count() == 2

    # 3. Update existing app via UPSERT (update official_name)
    sample_apps[0]["official_name"] = "Groww: Stocks, MF & IPO"
    app_repo.sync_from_config(sample_apps)
    assert app_repo.count() == 2
    updated = app_repo.get_by_internal_id("groww")
    assert updated["app_name"] == "Groww: Stocks, MF & IPO"

    # 4. Add new app via sync (count becomes 3)
    new_app = {
        "internal_id": "indmoney",
        "official_name": "INDmoney: Wealth Management",
        "developer_name": "Finzoom Investment Advisors",
        "apple_app_store": {"app_id": "1475730335"},
        "google_play_store": {"package_name": "com.indwealth"},
        "app_role": "PEER_BENCHMARK",
        "verification_status": "VERIFIED",
    }
    app_repo.sync_from_config(sample_apps + [new_app])
    assert app_repo.count() == 3

    # 5. Source routes UPSERT and idempotency
    sample_sources = [
        {
            "source_id": "apple_app_store_rss",
            "source_name": "Apple App Store Public RSS Feed",
            "source_family": "apple_app_store",
            "collection_method": "rss_feed",
            "technical_availability": "PRODUCTION_READY",
            "permission_status": "PUBLIC_PERMITTED",
            "enabled": True,
            "allowed_fields": ["review_id", "author", "rating", "title", "content"],
        }
    ]
    source_repo.sync_from_config(sample_sources)
    assert len(source_repo.list_all()) == 1
    # Repeated sync
    source_repo.sync_from_config(sample_sources)
    assert len(source_repo.list_all()) == 1

    # 6. Checkpoint UPSERT and idempotency
    ckpt = {
        "app_id": "groww",
        "storefront": "IN",
        "collection_method": "apple_app_store_rss",
        "last_successful_page": 5,
        "last_seen_review_id": "REV-12345",
        "total_reviews_collected": 250,
    }
    ckpt_repo.save_checkpoint(ckpt)
    saved = ckpt_repo.get_checkpoint("groww", "IN", "apple_app_store_rss")
    assert saved is not None
    assert saved["last_successful_page"] == 5

    # Update checkpoint
    ckpt["last_successful_page"] = 10
    ckpt_repo.save_checkpoint(ckpt)
    updated_ckpt = ckpt_repo.get_checkpoint("groww", "IN", "apple_app_store_rss")
    assert updated_ckpt["last_successful_page"] == 10
    assert len(ckpt_repo.list_checkpoints()) == 1


def test_regression_issue_13_ensure_postgres_constraints_and_sequences():
    """Verify that _ensure_postgres_constraints_and_sequences executes the required DDL checks idempotently."""
    db = DatabaseConnection(db_path="postgresql://mock_user:mock_pass@mock_host:5432/mock_db")
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    def mock_exec(query, params=None):
        q_str = str(query)
        result = MagicMock()
        if "pg_constraint" in q_str:
            result.fetchall.return_value = [("uq_apps_internal_app_id",), ("uq_source_routes_source_id",), ("uq_checkpoints_composite",)]
        elif "information_schema.tables" in q_str:
            result.scalar.return_value = 1
        elif "column_default" in q_str:
            result.scalar.return_value = "nextval('some_seq')"
        elif "MAX(" in q_str:
            result.scalar.return_value = 42
        else:
            result.scalar.return_value = None
        return result

    mock_conn.execute.side_effect = mock_exec
    db._ensure_postgres_constraints_and_sequences(mock_engine)
    assert mock_engine.begin.called




