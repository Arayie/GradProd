"""
Navigation and Layout Components for Growww Discovery Engine (Phase 6)
Provides high-contrast styles, section-based navigation, role switching, and research disclaimers.
"""

import streamlit as st
from core.auth import AuthService

PRIMARY_COLOR = "#00D09C"      # Groww brand green
SECONDARY_COLOR = "#1E3A2F"    # Deep research dark green
BG_LIGHT = "#F8FAFC"           # Subtle light background

PAGE_DEFINITIONS = [
    # SECTION 1: OVERVIEW
    ("Executive Overview", "📊", "OVERVIEW"),
    
    # SECTION 2: DATA & SOURCES
    ("Source Manager", "📥", "DATA & SOURCES"),
    ("Collection History", "📜", "DATA & SOURCES"),
    ("Review Explorer", "🔎", "DATA & SOURCES"),
    ("SIP Data Quality", "🔬", "DATA & SOURCES"),
    
    # SECTION 3: RESEARCH & INSIGHTS
    ("SIP Journey Explorer", "🗺️", "RESEARCH & INSIGHTS"),
    ("Investor Behaviour", "🧠", "RESEARCH & INSIGHTS"),
    ("Theme Explorer", "🏷️", "RESEARCH & INSIGHTS"),
    ("App Comparison", "⚖️", "RESEARCH & INSIGHTS"),
    
    # SECTION 4: OPPORTUNITY DISCOVERY
    ("Opportunity Radar", "🎯", "OPPORTUNITY DISCOVERY"),
    ("Opportunity Detail", "📋", "OPPORTUNITY DISCOVERY"),
    ("12M Retention Simulator", "🔮", "OPPORTUNITY DISCOVERY"),
    
    # SECTION 5: AI & VALIDATION
    ("AI Evidence Log", "⚡", "AI & VALIDATION"),
    ("Model Validation", "✅", "AI & VALIDATION"),
    ("Human Validation", "✍️", "AI & VALIDATION"),
    
    # SECTION 6: REPORTS & EXPORTS
    ("Exports & Reports", "📦", "REPORTS"),
]

def apply_custom_styles():
    """Injects financial research dashboard CSS styling with high-contrast, professional typography."""
    st.markdown(f"""
        <style>
            /* Main container layout */
            .main .block-container {{
                padding-top: 1.8rem;
                padding-bottom: 2.5rem;
                max-width: 1240px;
            }}
            /* Header accent */
            .groww-brand-title {{
                color: {SECONDARY_COLOR};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 2.2rem;
                font-weight: 800;
                letter-spacing: -0.03em;
                margin-bottom: 0.2rem;
            }}
            .groww-brand-subtitle {{
                color: #475569;
                font-size: 0.98rem;
                font-weight: 600;
                margin-bottom: 1.5rem;
            }}
            /* High-Contrast Professional Metric Card Styling */
            div[data-testid="stMetric"] {{
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                border-radius: 8px !important;
                padding: 1.1rem 1.25rem !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            }}
            /* Metric labels: High contrast dark text on white cards */
            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricLabel"] *,
            div[data-testid="stMetricLabel"] p,
            div[data-testid="stMetricLabel"] span,
            div[data-testid="stMetricLabel"] label,
            div[data-testid="stMetricLabel"] div {{
                font-size: 0.80rem !important;
                color: #0F172A !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.05em !important;
            }}
            /* Metric values: Deep dark green/black, bold */
            div[data-testid="stMetricValue"],
            div[data-testid="stMetricValue"] *,
            div[data-testid="stMetricValue"] div,
            div[data-testid="stMetricValue"] span {{
                font-size: 1.85rem !important;
                color: {SECONDARY_COLOR} !important;
                font-weight: 800 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            }}
            /* Section headers */
            h2, h3, h4 {{
                color: #0F172A !important;
                font-weight: 700 !important;
            }}
            /* Table polish */
            .stDataFrame {{
                border-radius: 8px;
                border: 1px solid #CBD5E1;
            }}
            /* Alert banner */
            .demo-banner {{
                background-color: #FEF3C7;
                border-left: 4px solid #D97706;
                padding: 0.85rem 1.1rem;
                border-radius: 6px;
                color: #78350F;
                font-size: 0.92rem;
                margin-bottom: 1.5rem;
                font-weight: 500;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
            }}
            /* Card wrapper for charts & content */
            .chart-card {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 1.25rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            }}
        </style>
    """, unsafe_allow_html=True)

def render_header(title: str, subtitle: str = ""):
    """Renders consistent top product header."""
    sub_html = f'<p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">{subtitle}</p>' if subtitle else ''
    st.markdown(f"""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Phase 6</div>
            <h2 style="color: #1E293B; font-weight: 700; margin-top: 1rem; margin-bottom: 0.5rem;">{title}</h2>
            {sub_html}
        </div>
    """, unsafe_allow_html=True)

def render_sidebar() -> str:
    """Renders sidebar navigation, RBAC role switcher, and governance alerts."""
    with st.sidebar:
        st.markdown(f"""
            <div style="padding: 0.5rem 0; margin-bottom: 0.8rem;">
                <h3 style="color: {SECONDARY_COLOR}; margin: 0; font-weight: 800; font-size: 1.4rem;">GROWWW</h3>
                <small style="color: #64748B; font-weight: 600;">Investor Discovery Engine • Phase 6</small>
            </div>
        """, unsafe_allow_html=True)

        page_names = [p[0] for p in PAGE_DEFINITIONS]
        if "current_page" not in st.session_state or st.session_state.current_page not in page_names:
            st.session_state.current_page = "Executive Overview"

        # Format function with emoji
        name_to_icon = {p[0]: p[1] for p in PAGE_DEFINITIONS}
        curr_idx = page_names.index(st.session_state.current_page)

        selected = st.radio(
            "Navigation Menu",
            options=page_names,
            format_func=lambda x: f"{name_to_icon.get(x, '📄')} {x}",
            index=curr_idx,
            label_visibility="collapsed"
        )
        st.session_state.current_page = selected

        # Role-Based Access Control Switcher
        AuthService.render_role_switcher()

        st.markdown("---")
        st.caption("RESEARCH GOVERNANCE")
        st.info("Public store reviews represent discovery evidence, not verified customer account retention.")

        return selected
