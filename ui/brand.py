"""
GROWWW Design System & Brand Asset Utilities.
Centralizes the Groww dark navy fintech aesthetic (#0B1020),
brand colors, logo assets, and custom component helpers.
"""

import os
import base64
from typing import Dict, Any
import streamlit as st

# =============================================================================
# COLOR PALETTE (GROWW FINTECH DARK DESIGN LANGUAGE)
# =============================================================================
NAVY_BG = "#0B1020"           # Deep dark navy main background
NAVY_SURFACE = "#111827"      # Slightly lighter navy surface
NAVY_CARD = "#111B2D"         # Card background
NAVY_CARD_HOVER = "#16233B"   # Card hover state
NAVY_BORDER = "#243247"       # Subtle card border
NAVY_BORDER_SUBTLE = "rgba(255, 255, 255, 0.07)"

# Brand Accents
GROWW_GREEN = "#00D09C"       # Primary Groww brand green / turquoise
GROWW_GREEN_HOVER = "#00B887"
GROWW_GREEN_BG = "rgba(0, 208, 156, 0.12)"
GROWW_BLUE = "#4E68FF"        # Secondary Groww blue
GROWW_BLUE_BG = "rgba(78, 104, 255, 0.12)"
GROWW_AMBER = "#F59E0B"       # Warning / In-progress
GROWW_AMBER_BG = "rgba(245, 158, 11, 0.12)"
GROWW_RED = "#EF4444"         # Critical friction
GROWW_RED_BG = "rgba(239, 68, 68, 0.12)"

# Typography Colors
TEXT_PRIMARY = "#F8FAFC"      # White primary text
TEXT_SECONDARY = "#94A3B8"    # Muted slate secondary text
TEXT_MUTED = "#64748B"        # Subtle tertiary text

# Path to Groww Logo Assets
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO_SVG_PATH = os.path.join(REPO_ROOT, "Groww", "Groww_Groww_White_Logo_copy_0.svg")
LOGO_PNG_PATH = os.path.join(REPO_ROOT, "Groww", "Groww_Groww_White_Logo_copy_1.png")


@st.cache_data
def get_groww_logo_data_uri() -> str:
    """
    Returns the vector SVG Groww logo encoded as a base64 Data URI.
    Ensures 100% reliable rendering on local development and Streamlit Cloud.
    Falls back to PNG if SVG is unavailable.
    """
    if os.path.exists(LOGO_SVG_PATH):
        try:
            with open(LOGO_SVG_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            return f"data:image/svg+xml;base64,{b64}"
        except Exception:
            pass

    if os.path.exists(LOGO_PNG_PATH):
        try:
            with open(LOGO_PNG_PATH, "rb") as f:
                content = f.read()
            b64 = base64.b64encode(content).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        except Exception:
            pass

    return ""


def get_groww_logo_html(height: int = 34) -> str:
    """Returns responsive inline HTML for the Groww logo."""
    uri = get_groww_logo_data_uri()
    if not uri:
        return f'<span style="font-weight: 800; font-size: 1.4rem; color: {GROWW_GREEN};">GROWWW</span>'
    return f"""
    <div style="display: inline-flex; align-items: center;">
        <img src="{uri}" alt="Groww" style="height: {height}px; width: auto; object-fit: contain; vertical-align: middle;" />
    </div>
    """


def get_plotly_dark_layout(is_cartesian: bool = True) -> Dict[str, Any]:
    """Returns standardized Plotly dark theme layout matching the Groww dashboard palette."""
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            color=TEXT_SECONDARY,
            size=12,
        ),
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(
            font=dict(color=TEXT_SECONDARY, size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=NAVY_CARD,
            font_size=12,
            font_family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            font_color=TEXT_PRIMARY,
            bordercolor=NAVY_BORDER,
        ),
    )
    if is_cartesian:
        layout["xaxis"] = dict(
            gridcolor="#1E293B",
            zerolinecolor="#1E293B",
            tickfont=dict(color=TEXT_MUTED, size=11),
            titlefont=dict(color=TEXT_SECONDARY, size=12),
        )
        layout["yaxis"] = dict(
            gridcolor="#1E293B",
            zerolinecolor="#1E293B",
            tickfont=dict(color=TEXT_MUTED, size=11),
            titlefont=dict(color=TEXT_SECONDARY, size=12),
        )
    return layout
