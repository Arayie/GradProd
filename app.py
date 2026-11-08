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
from ui.navigation import apply_custom_styles, render_navigation

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
    initial_sidebar_state="collapsed"
)

def init_app():
    """Initializes database schema, seeds opportunities, and initializes authentication."""
    if "db_initialized" not in st.session_state:
        db_mgr = get_database_manager()
        db_mgr.initialize()
        AuthService.init_session()
        st.session_state.db_initialized = True

PAGE_MAP = {
    # Group 1: Overview
    "Executive Overview": executive_overview.render,
    "Overview": executive_overview.render,
    # Group 2: Research & Data
    "Source Manager": source_manager_ui.render,
    "Collection History": collection_history_ui.render,
    "Review Explorer": review_explorer_ui.render,
    "SIP Data Quality": sip_quality.render,
    "SIP Journey Explorer": sip_journey_explorer.render,
    "Investor Behaviour": investor_behaviour.render,
    # Group 3: Intelligence
    "Theme Explorer": theme_explorer.render,
    "App Comparison": app_comparison.render,
    "Opportunity Radar": opportunity_radar.render,
    "Opportunity Detail": opportunity_detail.render,
    "12M Retention Simulator": retention_model_ui.render,
    # Group 4: Governance
    "AI Evidence Log": ai_evidence_log_ui.render,
    "Model Validation": model_validation_ui.render,
    "Human Validation": human_validation_ui.render,
    "Exports & Reports": exports_reports.render,
    "Exports and Reports": exports_reports.render,
}

def main():
    """Main routing and execution function."""
    init_app()
    apply_custom_styles()
    current_page = render_navigation()

    render_fn = PAGE_MAP.get(current_page)
    if render_fn:
        render_fn()
    else:
        st.error(f"Unknown page route: '{current_page}'. Defaulting to Executive Overview.")
        executive_overview.render()

if __name__ == "__main__":
    main()
