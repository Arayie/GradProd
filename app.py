"""
Growww – AI-Powered Investor Discovery Engine
Main Streamlit Application Entrypoint (Phase 6 Architecture)
"""
import os
import sys

# Ensure local workspace packages in lib/ and project root are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import streamlit as st
from core.database_manager import get_database_manager
from core.auth import AuthService
from ui.navigation import apply_custom_styles, render_sidebar

# Phase 6 Full Page Suite
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

# Configure page layout
st.set_page_config(
    page_title="GROWWW – Investor Discovery Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_app():
    """Initializes database schema, seeds opportunities, and initializes authentication."""
    if "db_initialized" not in st.session_state:
        db_mgr = get_database_manager()
        db_mgr.initialize()
        AuthService.init_session()
        st.session_state.db_initialized = True

def main():
    """Main routing and execution function."""
    init_app()
    apply_custom_styles()

    # Enforce authentication gate in production mode
    if not AuthService.check_auth_gate():
        return

    current_page = render_sidebar()

    # SECTION 1: OVERVIEW
    if current_page in ("Executive Overview", "Overview"):
        executive_overview.render()

    # SECTION 2: DATA & SOURCES
    elif current_page == "Source Manager":
        source_manager_ui.render()
    elif current_page == "Collection History":
        collection_history_ui.render()
    elif current_page == "Review Explorer":
        review_explorer_ui.render()
    elif current_page == "SIP Data Quality":
        sip_quality.render()

    # SECTION 3: RESEARCH & INSIGHTS
    elif current_page == "SIP Journey Explorer":
        sip_journey_explorer.render()
    elif current_page == "Investor Behaviour":
        investor_behaviour.render()
    elif current_page == "Theme Explorer":
        theme_explorer.render()
    elif current_page == "App Comparison":
        app_comparison.render()

    # SECTION 4: OPPORTUNITY DISCOVERY
    elif current_page == "Opportunity Radar":
        opportunity_radar.render()
    elif current_page == "Opportunity Detail":
        opportunity_detail.render()
    elif current_page == "12M Retention Simulator":
        retention_model_ui.render()

    # SECTION 5: AI & VALIDATION
    elif current_page == "AI Evidence Log":
        ai_evidence_log_ui.render()
    elif current_page == "Model Validation":
        model_validation_ui.render()
    elif current_page == "Human Validation":
        human_validation_ui.render()

    # SECTION 6: REPORTS & EXPORTS
    elif current_page in ("Exports & Reports", "Exports and Reports"):
        exports_reports.render()

    else:
        st.error(f"Unknown page route: {current_page}")

if __name__ == "__main__":
    main()
