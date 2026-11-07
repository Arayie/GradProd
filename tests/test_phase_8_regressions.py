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

    # Already qualified URLs are preserved
    url3 = "postgresql+psycopg2://user:pass@host/db"
    assert normalize_database_url(url3) == url3

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
        assert "Production PostgreSQL database connection failed" in str(exc_info.value)
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
    db = DatabaseConnection()
    db.is_postgres = True
    db.raw_url = "postgresql://user:pass@host/db"

    # Case A: Table already exists (idempotent, no DDL executed)
    with patch("sqlalchemy.create_engine") as mock_engine_factory:
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = "public.reviews"
        mock_engine_factory.return_value = mock_engine

        db.initialize_schema()
        assert mock_conn.execute.called

    # Case B: Table does not exist (empty database, executes DDL from postgres_schema.sql)
    with patch("sqlalchemy.create_engine") as mock_engine_factory:
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.scalar.return_value = None  # Not existing
        mock_engine_factory.return_value = mock_engine

        db.initialize_schema()
        # Verify statements were executed
        assert mock_conn.execute.call_count > 1

    # Case C: Missing schema file raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        db._initialize_postgres_schema(schema_file="/nonexistent/path/postgres_schema.sql")

    # Case D: Database connection failure propagates RuntimeError without SQLite fallback
    with patch("sqlalchemy.create_engine") as mock_engine_factory:
        mock_engine_factory.side_effect = Exception("Connection timed out")
        with pytest.raises(RuntimeError) as exc_info:
            db.initialize_schema()
        assert "PostgreSQL schema initialization failed" in str(exc_info.value)
        assert db.is_postgres is True


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

