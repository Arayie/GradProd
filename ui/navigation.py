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
    get_groww_logo_data_uri, get_groww_logo_html
)

# =============================================================================
# LOGICAL NAVIGATION GROUPS (PART 2 REQUIREMENT)
# Exactly 16 modules organized into 4 logical groups
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
PAGE_TO_ICON: Dict[str, str] = {}
for g_name, g_info in NAVIGATION_GROUPS.items():
    for p_name, icon, _ in g_info["pages"]:
        PAGE_TO_GROUP[p_name] = g_name
        PAGE_TO_ICON[p_name] = icon

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
    Zero preformatted code-block artifacts or white background overrides.
    """
    css = f"""
        <style>
            /* 1. Root & App Background */
            html, body, [data-testid="stAppViewContainer"], .main {{
                background-color: {NAVY_BG} !important;
                color: {TEXT_PRIMARY} !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            }}

            /* Main container padding */
            .main .block-container {{
                padding-top: 1.0rem !important;
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
                padding: 0.75rem 1.1rem;
                background-color: {NAVY_CARD};
                border: 1px solid {NAVY_BORDER};
                border-radius: 12px;
                margin-bottom: 1.0rem;
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
                font-size: 0.74rem;
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

            /* 4. High-Contrast Premium Metric Cards (Dark Fintech Theme) */
            div[data-testid="stMetric"] {{
                background-color: {NAVY_CARD} !important;
                border: 1px solid {NAVY_BORDER} !important;
                border-radius: 12px !important;
                padding: 1.1rem 1.25rem !important;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
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
                border-bottom: 2px solid transparent !important;
                padding: 0.6rem 1rem !important;
            }}
            button[data-baseweb="tab"][aria-selected="true"] {{
                color: {GROWW_GREEN} !important;
                border-bottom: 2px solid {GROWW_GREEN} !important;
            }}

            /* 10. Horizontal Radio Pills */
            div[data-testid="stRadio"] > div[role="radiogroup"] {{
                display: flex !important;
                flex-direction: row !important;
                gap: 8px !important;
                flex-wrap: wrap !important;
            }}
            div[data-testid="stRadio"] label {{
                background-color: {NAVY_CARD} !important;
                border: 1px solid {NAVY_BORDER} !important;
                border-radius: 8px !important;
                padding: 0.4rem 0.85rem !important;
                margin: 0 !important;
                cursor: pointer !important;
            }}
            div[data-testid="stRadio"] label:hover {{
                border-color: {GROWW_GREEN} !important;
            }}
            div[data-testid="stRadio"] label span {{
                color: {TEXT_PRIMARY} !important;
                font-weight: 600 !important;
                font-size: 0.88rem !important;
            }}

            /* 11. Alerts and Banners */
            .groww-banner {{
                background-color: rgba(78, 104, 255, 0.08);
                border-left: 4px solid {GROWW_BLUE};
                border-radius: 8px;
                padding: 0.85rem 1.1rem;
                color: {TEXT_PRIMARY};
                font-size: 0.88rem;
                margin-bottom: 1.25rem;
            }}

            /* 12. Inputs and Selectboxes */
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

            /* Dividers */
            hr {{
                border-color: {NAVY_BORDER} !important;
                margin: 1.25rem 0 !important;
            }}
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = ""):
    """Renders consistent top product sub-header matching the Groww dark design."""
    sub_html = f'<p style="color: {TEXT_SECONDARY}; font-size: 0.92rem; margin-bottom: 1.25rem;">{subtitle}</p>' if subtitle else ''
    html = f'<div style="margin-bottom: 0.8rem;"><h2 style="color: {TEXT_PRIMARY}; font-weight: 700; margin-top: 0.4rem; margin-bottom: 0.2rem; font-size: 1.5rem;">{title}</h2>{sub_html}</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_top_header():
    """
    Renders top navigation header with Groww vector logo, product title,
    and active user role badge.
    Built with clean single-line HTML to prevent markdown preformatted code blocks.
    """
    uri = get_groww_logo_data_uri()
    current_role = AuthService.get_current_role().value
    current_user = AuthService.get_current_user()

    col_brand, col_user = st.columns([3, 1])
    with col_brand:
        brand_html = (
            f'<div class="groww-top-navbar" style="margin-bottom: 0px;">'
            f'<div class="groww-brand-wrapper">'
            f'<img src="{uri}" alt="Groww" style="height: 34px; width: auto; object-fit: contain; vertical-align: middle;" />'
            f'<div style="border-left: 1px solid {NAVY_BORDER}; padding-left: 14px;">'
            f'<div class="groww-product-title">GROWWW</div>'
            f'<div class="groww-product-subtitle">AI-Powered Investor Discovery Engine</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)

    with col_user:
        user_html = (
            f'<div class="groww-top-navbar" style="margin-bottom: 0px; justify-content: flex-end;">'
            f'<div class="groww-profile-pill">'
            f'<span style="color: {GROWW_GREEN};">●</span>'
            f'<span>Role: <strong>{current_role}</strong> ({current_user})</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(user_html, unsafe_allow_html=True)


def render_navigation() -> str:
    """
    Renders the modern two-tier grouped navigation.
    Tier 1: Category selection across 4 groups (Overview, Research & Data, Intelligence, Governance)
    Tier 2: Specific module sub-navigation within the selected category.
    Guarantees that each category displays only its corresponding modules,
    and switching tabs reliably updates the active page without content bleeding.
    Returns the selected active page name string.
    """
    render_top_header()

    # Initialize state
    if "selected_group" not in st.session_state or st.session_state.selected_group not in NAVIGATION_GROUPS:
        st.session_state.selected_group = "Overview"

    if "current_page" not in st.session_state or st.session_state.current_page not in ALL_PAGE_NAMES:
        st.session_state.current_page = "Executive Overview"

    # Sync group if page was changed from external trigger
    expected_group = PAGE_TO_GROUP.get(st.session_state.current_page, "Overview")
    if expected_group != st.session_state.selected_group:
        st.session_state.selected_group = expected_group

    group_keys = list(NAVIGATION_GROUPS.keys())
    group_labels = [f"{NAVIGATION_GROUPS[g]['icon']} {g}" for g in group_keys]
    curr_group_idx = group_keys.index(st.session_state.selected_group)

    # -------------------------------------------------------------------------
    # Tier 1: Top Navigation Groups (Radio Pills)
    # -------------------------------------------------------------------------
    chosen_group_label = st.radio(
        "Navigation Category",
        options=group_labels,
        index=curr_group_idx,
        horizontal=True,
        label_visibility="collapsed",
        key="main_group_radio"
    )

    chosen_group = group_keys[group_labels.index(chosen_group_label)]

    # If the user switched groups, update group and set page to the group's first page
    if chosen_group != st.session_state.selected_group:
        st.session_state.selected_group = chosen_group
        st.session_state.current_page = NAVIGATION_GROUPS[chosen_group]["pages"][0][0]

    # -------------------------------------------------------------------------
    # Tier 2: Sub-Navigation Modules (Within Active Group)
    # -------------------------------------------------------------------------
    group_pages = [p[0] for p in NAVIGATION_GROUPS[chosen_group]["pages"]]
    page_icons = {p[0]: p[1] for p in NAVIGATION_GROUPS[chosen_group]["pages"]}

    if len(group_pages) == 1:
        # Single page group (Overview -> Executive Overview)
        selected_page = group_pages[0]
        st.session_state.current_page = selected_page
    else:
        # Multi-page groups (Research & Data, Intelligence, Governance)
        sub_labels = [f"{page_icons[p]} {p}" for p in group_pages]

        # Calculate index
        if st.session_state.current_page in group_pages:
            sub_idx = group_pages.index(st.session_state.current_page)
        else:
            sub_idx = 0
            st.session_state.current_page = group_pages[0]

        chosen_sub_label = st.radio(
            f"{chosen_group} Modules",
            options=sub_labels,
            index=sub_idx,
            horizontal=True,
            label_visibility="collapsed",
            key=f"sub_nav_radio_{chosen_group}"
        )

        selected_page = group_pages[sub_labels.index(chosen_sub_label)]
        st.session_state.current_page = selected_page

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Render companion sidebar (role switcher, database telemetry)
    render_sidebar_companion(selected_page)

    return selected_page


def render_sidebar_companion(active_page: str):
    """
    Renders streamlined companion controls inside the sidebar:
    - User authentication / role switcher
    - Current active module indicator
    - Live database and dataset telemetry badge
    - Research governance reminder
    """
    with st.sidebar:
        uri = get_groww_logo_data_uri()
        st.markdown(
            f'<div style="padding: 0.25rem 0 0.8rem 0; text-align: center;">'
            f'<img src="{uri}" alt="Groww" style="height: 28px; width: auto; object-fit: contain; vertical-align: middle;" />'
            f'<div style="font-size: 0.75rem; color: {TEXT_MUTED}; margin-top: 4px; font-weight: 600;">'
            f'INVESTOR DISCOVERY ENGINE • v2.0</div></div>',
            unsafe_allow_html=True
        )

        # Active Module Display
        group_name = PAGE_TO_GROUP.get(active_page, "Overview")
        icon = PAGE_TO_ICON.get(active_page, "📄")
        st.caption("ACTIVE RESEARCH MODULE")
        st.markdown(
            f'<div style="background-color: {NAVY_CARD}; border: 1px solid {GROWW_GREEN}44; border-left: 3px solid {GROWW_GREEN}; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.5rem;">'
            f'<div style="font-size: 0.72rem; color: {TEXT_MUTED}; text-transform: uppercase; font-weight: 700;">{group_name}</div>'
            f'<div style="font-size: 0.9rem; font-weight: 700; color: {TEXT_PRIMARY};">{icon} {active_page}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Role-Based Access Control Switcher
        AuthService.render_role_switcher()

        # Database Telemetry Badge
        st.markdown("---")
        st.caption("SYSTEM & DATASET STATUS")
        from database.connection import get_connection_diagnostics
        diag = get_connection_diagnostics()
        db_type = "Render PostgreSQL" if diag.get("driver", "").startswith("postgresql") else "SQLite Local"
        st.markdown(
            f'<div style="background-color: {NAVY_CARD}; border: 1px solid {NAVY_BORDER}; border-radius: 8px; padding: 0.65rem 0.85rem; font-size: 0.78rem;">'
            f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px;">'
            f'<span style="color: {TEXT_SECONDARY};">Database:</span>'
            f'<strong style="color: {GROWW_GREEN};">{db_type}</strong></div>'
            f'<div style="display: flex; justify-content: space-between; margin-bottom: 4px;">'
            f'<span style="color: {TEXT_SECONDARY};">SSL Mode:</span>'
            f'<span style="color: {TEXT_PRIMARY};">{diag.get("sslmode") or "N/A"}</span></div>'
            f'<div style="display: flex; justify-content: space-between;">'
            f'<span style="color: {TEXT_SECONDARY};">Sampling Frame:</span>'
            f'<strong style="color: {TEXT_PRIMARY};">3,790 Reviews</strong></div>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.caption("RESEARCH GOVERNANCE")
        st.markdown(
            f'<div style="font-size: 0.74rem; color: {TEXT_MUTED}; line-height: 1.35; padding: 0.2rem 0;">'
            f'Public store reviews reflect customer discovery signals, not internal account ledgers.'
            f'</div>',
            unsafe_allow_html=True
        )


def render_sidebar() -> str:
    """Backward-compatible entry point for app.py."""
    return render_navigation()
