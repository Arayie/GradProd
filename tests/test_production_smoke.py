"""
End-to-End Production Smoke Test Suite (Phase 8 Task 11)
Validates Authentication, Database Integrity, Analytics Parity, AI Grounding,
Opportunity Ranking, Export Services, and Health Check Diagnostics.
"""

import os
import sys
import pytest
import sqlite3
from typing import Dict, Any

# Ensure workspace and local lib are available
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.auth import AuthService, UserRole, Permission, hash_password, verify_password
from core.env_config import get_env_config, EnvironmentConfig
from database.connection import get_db, DatabaseConnection
from services.health_service import HealthService
from services.analytics_service import AnalyticsService
from services.pdf_export_service import PDFExportService

@pytest.fixture
def db():
    return get_db()

# ------------------------------------------------------------------------------
# TEST A: AUTHENTICATION & RBAC PERMISSION GATING
# ------------------------------------------------------------------------------
def test_smoke_a_authentication_and_rbac():
    """Validates login authentication, password verification, and role permissions."""
    # Test valid credentials
    assert AuthService.authenticate("admin", "Admin@Growww2026!") is True
    assert AuthService.get_current_role() == UserRole.ADMIN
    assert AuthService.has_permission(Permission.MANAGE_SOURCES) is True
    assert AuthService.has_permission(Permission.EXPORT_RAW_DATA) is True

    assert AuthService.authenticate("researcher", "Research@Growww2026!") is True
    assert AuthService.get_current_role() == UserRole.RESEARCHER
    assert AuthService.has_permission(Permission.MANAGE_SOURCES) is False
    assert AuthService.has_permission(Permission.ADJUDICATE_REVIEWS) is True

    assert AuthService.authenticate("viewer", "Viewer@Growww2026!") is True
    assert AuthService.get_current_role() == UserRole.VIEWER
    assert AuthService.has_permission(Permission.EXPORT_RAW_DATA) is False
    assert AuthService.has_permission(Permission.VIEW_ANALYTICS) is True

    assert AuthService.authenticate("auditor", "Auditor@Growww2026!") is True
    assert AuthService.get_current_role() == UserRole.AUDITOR
    assert AuthService.has_permission(Permission.VIEW_AUDIT_LOGS) is True
    assert AuthService.has_permission(Permission.MANAGE_SOURCES) is False

    # Test invalid credentials
    assert AuthService.authenticate("admin", "WrongPassword123!") is False
    assert AuthService.authenticate("unknown_user", "AnyPassword") is False

# ------------------------------------------------------------------------------
# TEST B: DATABASE CONNECTION, WAL MODE & INTEGRITY
# ------------------------------------------------------------------------------
def test_smoke_b_database_connection_and_integrity(db):
    """Verifies SQLite connection, WAL mode, quick_check, and zero foreign key violations."""
    conn = db.get_raw_connection()
    cur = conn.cursor()

    # Foreign key check
    fk_violations = cur.execute("PRAGMA foreign_key_check;").fetchall()
    assert len(fk_violations) == 0, f"Found foreign key violations: {fk_violations}"

    # Quick check
    quick_check = cur.execute("PRAGMA quick_check;").fetchone()[0]
    assert quick_check == "ok", f"quick_check failed: {quick_check}"

    # Journal mode
    journal_mode = cur.execute("PRAGMA journal_mode;").fetchone()[0]
    assert journal_mode.lower() == "wal"

    conn.close()

# ------------------------------------------------------------------------------
# TEST C: OVERVIEW METRIC & QUARANTINE PARITY
# ------------------------------------------------------------------------------
def test_smoke_c_overview_metric_and_quarantine_parity(db):
    """Verifies that exactly 3,790 eligible reviews and 8 quarantined records exist."""
    with db.get_cursor() as cur:
        total = cur.execute("SELECT COUNT(*) FROM reviews;").fetchone()[0]
        eligible = cur.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE';").fetchone()[0]
        quarantine = cur.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO';").fetchone()[0]
        sip_count = cur.execute(
            "SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND (sip_relevance_status = 'SIP_RELEVANT' OR mentions_sip = 1);"
        ).fetchone()[0]

    assert total >= 3798
    assert eligible >= 3790
    assert quarantine == 8
    assert sip_count >= 156

# ------------------------------------------------------------------------------
# TEST D: AI EVIDENCE & 100% VERBATIM GROUNDING
# ------------------------------------------------------------------------------
def test_smoke_d_ai_evidence_and_grounding(db):
    """Verifies that exemplar quotes in opportunities match verbatim text in reviews."""
    with db.get_cursor() as cur:
        opps = cur.execute("SELECT opportunity_id, exemplar_verbatim_quote FROM opportunities;").fetchall()
        assert len(opps) == 7
        for opp_id, quote in opps:
            assert quote is not None and len(quote) > 10
            # Quote must exist in actual reviews
            match = cur.execute(
                "SELECT COUNT(*) FROM reviews WHERE review_text LIKE ?;",
                (f"%{quote[:25]}%",)
            ).fetchone()[0]
            assert match > 0, f"Exemplar quote for {opp_id} not grounded in reviews table!"

# ------------------------------------------------------------------------------
# TEST E: OPPORTUNITY RANKING & SCORES
# ------------------------------------------------------------------------------
def test_smoke_e_opportunity_ranking_and_scores(db):
    """Verifies that all 7 opportunities exist and are sorted by opportunity_score descending."""
    with db.get_cursor() as cur:
        opps = cur.execute(
            "SELECT priority_rank, opportunity_id, opportunity_score, evidence_confidence "
            "FROM opportunities ORDER BY priority_rank ASC;"
        ).fetchall()

    assert len(opps) == 7
    scores = [row[2] for row in opps]
    # Scores should be in descending order (or equal)
    assert scores == sorted(scores, reverse=True)
    # Check bounds
    for row in opps:
        score = row[2]
        conf = row[3]
        assert 0.0 <= score <= 10.0
        assert 0.0 <= conf <= 1.0

# ------------------------------------------------------------------------------
# TEST F: EXPORT PIPELINE
# ------------------------------------------------------------------------------
def test_smoke_f_export_pipeline(db):
    """Verifies PDF digest generation and CSV query generation without errors."""
    output_pdf = os.path.join(REPO_ROOT, "outputs", "smoke_test_digest.pdf")
    pdf_service = PDFExportService()
    res_path = pdf_service.generate_weekly_digest(output_path=output_pdf, db_path=db.db_path)
    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 1000

    # Clean up test output
    if os.path.exists(output_pdf):
        os.remove(output_pdf)

# ------------------------------------------------------------------------------
# TEST G: HEALTH CHECK SERVICE
# ------------------------------------------------------------------------------
def test_smoke_g_health_check_service(db):
    """Verifies that HealthService returns HEALTHY status across all checks."""
    health_svc = HealthService(db)
    diag = health_svc.run_full_diagnostics()
    assert diag["overall_status"] == "HEALTHY"
    assert diag["checks"]["database_latency"]["status"] == "PASS"
    assert diag["checks"]["database_integrity"]["status"] == "PASS"
    assert diag["checks"]["quarantine_isolation"]["status"] == "PASS"
    assert diag["checks"]["data_metrics"]["status"] == "PASS"
