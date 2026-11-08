"""
Tests for Groww Pulse 16-page navigation routing and test matrix.
Verifies all 16 page modules, routing definitions, transitions, and query execution.
"""
import pytest
from unittest.mock import MagicMock, patch
import app
from ui.navigation import NAVIGATION_GROUPS, PAGE_TO_GROUP, PAGE_TO_ICON, ALL_PAGE_NAMES
from core.database_manager import get_database_manager


def test_16_pages_defined_and_unique():
    """Verify exactly 16 modules are registered across the 4 logical groups."""
    assert len(ALL_PAGE_NAMES) == 16
    assert len(PAGE_TO_GROUP) == 16
    assert len(set(ALL_PAGE_NAMES)) == 16


def test_all_pages_mapped_in_app():
    """Verify every single registered page has an explicit routing function in PAGE_MAP."""
    for page_name in ALL_PAGE_NAMES:
        assert page_name in app.PAGE_MAP, f"Page '{page_name}' is missing from app.PAGE_MAP"
        assert callable(app.PAGE_MAP[page_name]), f"Page '{page_name}' mapping is not callable"


def test_navigation_test_matrix_transitions():
    """
    Tests sequential transitions across all 16 pages as specified in Issue 7:
    Executive Overview → Source Manager
    Source Manager → Collection History
    Collection History → Review Explorer
    Review Explorer → SIP Data Quality
    SIP Data Quality → SIP Journey Explorer
    SIP Journey Explorer → Investor Behaviour
    Investor Behaviour → Theme Explorer
    Theme Explorer → App Comparison
    App Comparison → Opportunity Radar
    Opportunity Radar → Opportunity Detail
    Opportunity Detail → 12M Retention Simulator
    12M Retention Simulator → AI Evidence Log
    AI Evidence Log → Model Validation
    Model Validation → Human Validation
    Human Validation → Exports & Reports
    """
    matrix_transitions = [
        ("Executive Overview", "Source Manager"),
        ("Source Manager", "Collection History"),
        ("Collection History", "Review Explorer"),
        ("Review Explorer", "SIP Data Quality"),
        ("SIP Data Quality", "SIP Journey Explorer"),
        ("SIP Journey Explorer", "Investor Behaviour"),
        ("Investor Behaviour", "Theme Explorer"),
        ("Theme Explorer", "App Comparison"),
        ("App Comparison", "Opportunity Radar"),
        ("Opportunity Radar", "Opportunity Detail"),
        ("Opportunity Detail", "12M Retention Simulator"),
        ("12M Retention Simulator", "AI Evidence Log"),
        ("AI Evidence Log", "Model Validation"),
        ("Model Validation", "Human Validation"),
        ("Human Validation", "Exports & Reports"),
    ]

    for from_page, to_page in matrix_transitions:
        assert from_page in app.PAGE_MAP
        assert to_page in app.PAGE_MAP
        # Verify destination maps to a distinct render function
        assert app.PAGE_MAP[from_page] != app.PAGE_MAP[to_page], (
            f"Transition {from_page} -> {to_page} failed: identical target function"
        )


def test_database_source_manager_cte_query():
    """Verify that Source Manager CTE aggregation query executes cleanly on SQLite and PostgreSQL."""
    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()
    cursor = conn.cursor()

    query = """
    WITH review_agg AS (
        SELECT 
            app_id,
            COUNT(id) as reviews_stored,
            MIN(review_created_at) as oldest_review,
            MAX(review_created_at) as newest_review
        FROM reviews
        WHERE store = 'apple_app_store'
        GROUP BY app_id
    )
    SELECT 
        a.internal_app_id,
        a.app_name,
        a.apple_app_id,
        a.apple_listing_url,
        COALESCE(r.reviews_stored, 0) as reviews_stored,
        r.oldest_review,
        r.newest_review
    FROM apps a
    LEFT JOIN review_agg r ON a.internal_app_id = r.app_id
    ORDER BY reviews_stored DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    assert len(rows) >= 8, f"Expected at least 8 apps, got {len(rows)}"
    app_ids = [r[0] for r in rows]
    assert "groww" in app_ids


def test_database_metrics_parity():
    """Verify dashboard metrics are backed by genuine database records."""
    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()
    cursor = conn.cursor()

    # 1. Total eligible reviews
    cursor.execute("SELECT count(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
    eligible_count = cursor.fetchone()[0]
    assert eligible_count == 3790

    # 2. Total apps
    cursor.execute("SELECT count(*) FROM apps")
    total_apps = cursor.fetchone()[0]
    assert total_apps == 8

    # 3. SIP relevant reviews (Direct + Indirect SIP relevance signals)
    cursor.execute("SELECT count(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND sip_relevance_status IN ('DIRECT_SIP_RELEVANT', 'INDIRECT_SIP_RELEVANT')")
    sip_relevant = cursor.fetchone()[0]
    assert sip_relevant == 158

    # 4. Total opportunities
    cursor.execute("SELECT count(*) FROM opportunities")
    total_opps = cursor.fetchone()[0]
    assert total_opps == 7


def test_all_16_pages_import_and_render_callable():
    """Verify that all 16 pages can be imported and their render function is properly configured."""
    for page_name in ALL_PAGE_NAMES:
        fn = app.PAGE_MAP[page_name]
        assert callable(fn), f"Page {page_name} render target is not callable"
        assert hasattr(fn, "__name__")
        assert fn.__name__ == "render", f"Page {page_name} target function should be named 'render'"
