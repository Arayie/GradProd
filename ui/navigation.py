"""
Navigation and Layout Components for Groww Discovery Engine.
Implements the Groww Pulse dark navy fintech aesthetic (#0B1020),
simplified grouped top navigation, logo branding, and RBAC controls.
"""

import streamlit as st
from typing import Dict, List, Tuple, Any
from core.auth import AuthService, UserRole
from ui.brand import (
    NAVY_BG, NAVY_SURFACE, NAVY_CARD, NAVY_BORDER,
    GROWW_GREEN, GROWW_BLUE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    get_groww_logo_html
)

# =============================================================================
# LOGICAL NAVIGATION GROUPS (PART 2 REQUIREMENT)
# =============================================================================
NAVIGATION_GROUPS: Dict[str, Dict[str, Any]] = {
    "Overview": {
        "icon": "📊",
        "description": "Executive Insights & Key Metrics",
        "pages": [
            ("Executive Overview", "📊", "High-level metrics, satisfaction trends, and priority opportunities"),
        ]
    },
    "Research & Data": {
        "icon": "📥",
        "description": "Store Sources & Feedback Ingestion",
        "pages": [
            ("Source Manager", "📥", "App Store RSS feeds & Google Play configuration"),
            ("Collection History", "📜", "Ingestion audit log and run telemetry"),
            ("Review Explorer", "🔎", "Search, filter and inspect raw customer reviews"),
            ("SIP Data Quality", "🔬", "PII minimization and data hygiene invariants"),
            ("SIP Journey Explorer", "🗺️", "8-stage SIP lifecycle feedback distribution"),
            ("Investor Behaviour", "🧠", "Intent, expectation, and behavioral triggers"),
        ]
    },
    "Intelligence": {
        "icon": "💡",
        "description": "Competitive Intelligence & Opportunities",
        "pages": [
            ("Theme Explorer", "🏷️", "Validated friction themes and frequency analysis"),
            ("App Comparison", "⚖️", "Cross-app peer benchmarking across 8 platforms"),
            ("Opportunity Radar", "🎯", "Prioritized product interventions and ranking"),
            ("Opportunity Detail", "📋", "Deep-dive hypothesis, guardrails, and metrics"),
            ("12M Retention Simulator", "🔮", "Retention curves and intervention impact modeling"),
        ]
    },
    "Governance": {
        "icon": "🛡️",
        "description": "AI Lineage & Validation",
        "pages": [
            ("AI Evidence Log", "⚡", "Inference lineage, prompts, and grounding spans"),
            ("Model Validation", "✅", "NLP classification accuracy and confusion matrices"),
            ("Human Validation", "✍️", "Human-in-the-loop review and label adjudication"),
            ("Exports & Reports", "📦", "Audit-ready dataset downloads and executive reports"),
        ]
    }
}

# Reverse lookup: page_name -> group_name
PAGE_TO_GROUP: Dict[str, str] = {}
for g_name, g_info in NAVIGATION_GROUPS.items():
    for p_name, _, _ in g_info["pages"]:
        PAGE_TO_GROUP[p_name] = g_name

ALL_PAGE_NAMES: List[str] = list(PAGE_TO_GROUP.keys())

# Backward-compatible list of (name, icon, group) for Phase 6 test suite
PAGE_DEFINITIONS: List[Tuple[str, str, str]] = [
    (p_name, icon, g_name.upper())
    for g_name, g_info in NAVIGATION_GROUPS.items()
    for p_name, icon, _ in g_info["pages"]
]


def apply_custom_styles():
    """
    Injects Groww Pulse fintech dark design language CSS styling.
    Dark navy background (#0B1020), card surfaces (#111B2D), emerald accents (#00D09C).
    """
    st.markdown(f"""
        <style>
            /* 1. Root & App Background */
            html, body, [data-testid="stAppViewContainer"], .main {{
                background-color: {NAVY_BG} !important;
                color: {TEXT_PRIMARY} !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            }}

            /* Main container padding */
            .main .block-container {{
                padding-top: 1.2rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1360px !important;
            }}

            /* 2. Sidebar Styling */
            section[data-testid="stSidebar"] {{
                background-color: #0E1526 !important;
                border-right: 1px solid {NAVY_BORDER} !important;
            }}
            section[data-testid="stSidebar"] * {{
                color: {TEXT_PRIMARY};
            }}

            /* 3. Top Navigation Bar */
            .groww-top-navbar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.85rem 1.25rem;
                background-color: {NAVY_CARD};
                border: 1px solid {NAVY_BORDER};
                border-radius: 12px;
                margin-bottom: 1.25rem;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
            }}

            .groww-brand-wrapper {{
                display: flex;
                align-items: center;
                gap: 14px;
            }}

            .groww-product-title {{
                font-size: 1.35rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                color: {TEXT_PRIMARY};
                line-height: 1.1;
            }}

            .groww-product-subtitle {{
                font-size: 0.76rem;
                color: {GROWW_GREEN};
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }}

            .groww-profile-pill {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background-color: rgba(0, 208, 156, 0.1);
                border: 1px solid rgba(0, 208, 156, 0.25);
                color: {GROWW_GREEN};
                padding: 0.35rem 0.85rem;
                border-radius: 20px;
                font-size: 0.82rem;
                font-weight: 600;
            }}

            /* 4. High-Contrast Premium Metric Cards */
            div[data-testid="stMetric"] {{
                background-color: {NAVY_CARD} !important;
                border: 1px solid {NAVY_BORDER} !important;
                border-radius: 12px !important;
                padding: 1.1rem 1.25rem !important;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
                transition: transform 0.15s ease, border-color 0.15s ease !important;
            }}
            div[data-testid="stMetric"]:hover {{
                border-color: {GROWW_GREEN} !important;
            }}

            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricLabel"] * {{
                font-size: 0.78rem !important;
                color: {TEXT_SECONDARY} !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.05em !important;
            }}

            div[data-testid="stMetricValue"],
            div[data-testid="stMetricValue"] * {{
                font-size: 1.85rem !important;
                color: {GROWW_GREEN} !important;
                font-weight: 800 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            }}

            div[data-testid="stMetricDelta"],
            div[data-testid="stMetricDelta"] * {{
                color: {TEXT_MUTED} !important;
                font-size: 0.78rem !important;
                font-weight: 500 !important;
            }}

            /* 5. Custom Groww Card Container */
            .groww-card {{
                background-color: {NAVY_CARD};
                border: 1px solid {NAVY_BORDER};
                border-radius: 12px;
                padding: 1.25rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
            }}

            .groww-card-header {{
                font-size: 1.05rem;
                font-weight: 700;
                color: {TEXT_PRIMARY};
                margin-bottom: 0.4rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}

            .groww-card-subtitle {{
                font-size: 0.82rem;
                color: {TEXT_SECONDARY};
                margin-bottom: 1rem;
            }}

            /* 6. Typography */
            h1, h2, h3, h4 {{
                color: {TEXT_PRIMARY} !important;
                font-weight: 700 !important;
                letter-spacing: -0.02em !important;
            }}

            p, span, label {{
                color: {TEXT_SECONDARY};
            }}

            /* 7. Streamlit DataFrames */
            div[data-testid="stDataFrame"] {{
                background-color: {NAVY_CARD} !important;
                border: 1px solid {NAVY_BORDER} !important;
                border-radius: 10px !important;
                overflow: hidden !important;
            }}

            /* 8. Buttons */
            div.stButton > button {{
                background-color: {GROWW_GREEN} !important;
                color: #0B1020 !important;
                font-weight: 700 !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 0.45rem 1.1rem !important;
                font-size: 0.88rem !important;
                transition: opacity 0.2s ease, transform 0.1s ease !important;
            }}
            div.stButton > button:hover {{
                opacity: 0.92 !important;
                transform: translateY(-1px) !important;
            }}

            div.stDownloadButton > button {{
                background-color: {NAVY_CARD} !important;
                color: {GROWW_GREEN} !important;
                border: 1px solid {GROWW_GREEN} !important;
                font-weight: 700 !important;
                border-radius: 8px !important;
            }}

            /* 9. Streamlit Tabs */
            button[data-baseweb="tab"] {{
                background-color: transparent !important;
                color: {TEXT_SECONDARY} !important;
                font-weight: 600 !important;
                border-radius: 0px !important;
                border-bottom: 2px solid transparent !important;
                padding: 0.6rem 1rem !important;
            }}
            button[data-baseweb="tab"][aria-selected="true"] {{
                color: {GROWW_GREEN} !important;
                border-bottom: 2px solid {GROWW_GREEN} !important;
            }}

            /* 10. Segmented control / Pills overrides */
            div[data-testid="stSegmentedControl"] button[aria-selected="true"],
            div[data-testid="stPills"] button[aria-selected="true"] {{
                background-color: {GROWW_GREEN} !important;
                color: #0B1020 !important;
                font-weight: 700 !important;
            }}

            div[data-testid="stSegmentedControl"] button[aria-selected="false"],
            div[data-testid="stPills"] button[aria-selected="false"] {{
                background-color: {NAVY_CARD} !important;
                color: {TEXT_SECONDARY} !important;
                border: 1px solid {NAVY_BORDER} !important;
            }}

            /* 11. Alerts and Banners */
            .groww-banner {{
                background-color: rgba(78, 104, 255, 0.08);
                border-left: 4px solid {GROWW_BLUE};
                border-top: 1px solid rgba(78, 104, 255, 0.2);
                border-right: 1px solid rgba(78, 104, 255, 0.2);
                border-bottom: 1px solid rgba(78, 104, 255, 0.2);
                border-radius: 8px;
                padding: 0.85rem 1.1rem;
                color: {TEXT_PRIMARY};
                font-size: 0.88rem;
                margin-bottom: 1.25rem;
            }}

            /* 12. Inputs, Selectboxes, Multiselects */
            div[data-baseweb="select"] > div {{
                background-color: {NAVY_CARD} !important;
                border-color: {NAVY_BORDER} !important;
                color: {TEXT_PRIMARY} !important;
            }}

            div[data-baseweb="input"] > input {{
                background-color: {NAVY_CARD} !important;
                border-color: {NAVY_BORDER} !important;
                color: {TEXT_PRIMARY} !important;
            }}

            /* Subtle HR divider */
            hr {{
                border-color: {NAVY_BORDER} !important;
                margin: 1.5rem 0 !important;
            }}
        </style>
    """, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = ""):
    """Renders consistent top product sub-header matching the Groww dark design."""
    sub_html = f'<p style="color: {TEXT_SECONDARY}; font-size: 0.92rem; margin-bottom: 1.25rem;">{subtitle}</p>' if subtitle else ''
    st.markdown(f"""
        <div style="margin-bottom: 0.8rem;">
            <h2 style="color: {TEXT_PRIMARY}; font-weight: 700; margin-top: 0.4rem; margin-bottom: 0.2rem; font-size: 1.5rem;">{title}</h2>
            {sub_html}
        </div>
    """, unsafe_allow_html=True)


def render_top_header():
    """
    Renders top navigation header with Groww vector logo, product title,
    active user role badge, and dataset status.
    """
    logo_html = get_groww_logo_html(height=34)
    current_role = AuthService.get_current_role().value
    current_user = AuthService.get_current_user()

    st.markdown(f"""
        <div class="groww-top-navbar">
            <div class="groww-brand-wrapper">
                {logo_html}
                <div style="border-left: 1px solid {NAVY_BORDER}; padding-left: 14px;">
                    <div class="groww-product-title">GROWWW</div>
                    <div class="groww-product-subtitle">AI-Powered Investor Discovery Engine</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="groww-profile-pill">
                    <span style="color: {GROWW_GREEN};">●</span>
                    <span>Role: <strong>{current_role}</strong> ({current_user})</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_navigation() -> str:
    """
    Renders the modern grouped top navigation.
    Organizes 16 modules into 4 top-level groups (Part 2 requirement):
      1. Overview (Executive Overview)
      2. Research & Data (6 modules)
      3. Intelligence (5 modules)
      4. Governance (4 modules)
    Returns the selected active page name string.
    """
    render_top_header()

    # Initialize session state for navigation
    if "current_page" not in st.session_state or st.session_state.current_page not in ALL_PAGE_NAMES:
        st.session_state.current_page = "Executive Overview"

    active_page = st.session_state.current_page
    current_group = PAGE_TO_GROUP.get(active_page, "Overview")

    # 1. Main Group Navigation Tabs
    group_options = list(NAVIGATION_GROUPS.keys())
    group_labels = [f"{NAVIGATION_GROUPS[g]['icon']} {g}" for g in group_options]
    curr_group_idx = group_options.index(current_group)

    selected_group_label = st.pills(
        "Navigation Groups",
        options=group_labels,
        default=group_labels[curr_group_idx],
        label_visibility="collapsed",
        key="top_nav_group_selector"
    )

    # Parse selected group
    selected_group = group_options[curr_group_idx]
    if selected_group_label:
        for idx, lbl in enumerate(group_labels):
            if lbl == selected_group_label:
                selected_group = group_options[idx]
                break

    # If the user switched groups and the current page doesn't belong to the new group,
    # default to the first page of the new group
    group_pages = [p[0] for p in NAVIGATION_GROUPS[selected_group]["pages"]]
    if active_page not in group_pages:
        active_page = group_pages[0]
        st.session_state.current_page = active_page

    # 2. Secondary Sub-Navigation (Rendered only when group has multiple pages)
    if len(group_pages) > 1:
        page_icon_map = {p[0]: p[1] for p in NAVIGATION_GROUPS[selected_group]["pages"]}
        sub_labels = [f"{page_icon_map[p]} {p}" for p in group_pages]
        curr_page_idx = group_pages.index(active_page)

        sub_selection = st.segmented_control(
            f"{selected_group} Modules",
            options=sub_labels,
            default=sub_labels[curr_page_idx],
            label_visibility="collapsed",
            key=f"sub_nav_selector_{selected_group}"
        )

        if sub_selection:
            for idx, lbl in enumerate(sub_labels):
                if lbl == sub_selection:
                    active_page = group_pages[idx]
                    st.session_state.current_page = active_page
                    break

    # Also render companion sidebar controls (role switcher & quick-jump)
    render_sidebar_companion(active_page)

    return active_page


def render_sidebar_companion(active_page: str):
    """
    Renders streamlined companion controls inside the sidebar:
    - User authentication / role switcher
    - Quick jump to any page
    - Dataset and connection status badge
    - Research governance reminder
    """
    with st.sidebar:
        st.markdown(f"""
            <div style="padding: 0.25rem 0 0.8rem 0; text-align: center;">
                {get_groww_logo_html(height=28)}
                <div style="font-size: 0.75rem; color: {TEXT_MUTED}; margin-top: 4px; font-weight: 600;">
                    INVESTOR DISCOVERY ENGINE • v2.0
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Quick Jump Dropdown across all 16 pages
        st.caption("QUICK JUMP")
        quick_jump = st.selectbox(
            "Jump Directly to Page",
            options=ALL_PAGE_NAMES,
            index=ALL_PAGE_NAMES.index(active_page),
            label_visibility="collapsed",
            key="sidebar_quick_jump"
        )
        if quick_jump != active_page:
            st.session_state.current_page = quick_jump
            st.rerun()

        # Role-Based Access Control Switcher
        AuthService.render_role_switcher()

        # Database Telemetry Badge
        st.markdown("---")
        st.caption("SYSTEM & DATASET STATUS")
        from database.connection import get_connection_diagnostics
        diag = get_connection_diagnostics()
        db_type = "Render PostgreSQL" if diag.get("driver", "").startswith("postgresql") else "SQLite Local"
        st.markdown(f"""
            <div style="background-color: {NAVY_CARD}; border: 1px solid {NAVY_BORDER}; border-radius: 8px; padding: 0.65rem 0.85rem; font-size: 0.78rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: {TEXT_SECONDARY};">Database:</span>
                    <strong style="color: {GROWW_GREEN};">{db_type}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: {TEXT_SECONDARY};">SSL Mode:</span>
                    <span style="color: {TEXT_PRIMARY};">{diag.get('sslmode') or 'N/A'}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: {TEXT_SECONDARY};">Sampling Frame:</span>
                    <strong style="color: {TEXT_PRIMARY};">3,790 Reviews</strong>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.caption("RESEARCH GOVERNANCE")
        st.markdown(f"""
            <div style="font-size: 0.74rem; color: {TEXT_MUTED}; line-height: 1.35; padding: 0.2rem 0;">
                Public store reviews reflect customer discovery signals, not internal account ledgers.
            </div>
        """, unsafe_allow_html=True)


def render_sidebar() -> str:
    """Backward-compatible entry point for app.py."""
    return render_navigation()
