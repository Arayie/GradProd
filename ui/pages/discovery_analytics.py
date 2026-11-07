"""
SIP Discovery Analytics & Theme Frequency Dashboard (Phase 5)
Interactive quantification of recurring SIP friction themes across eligible sampling frames.
"""

import streamlit as st
import pandas as pd
import json
import os
from analytics.theme_frequency import ThemeFrequencyEngine

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Phase 5 Analytics</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">SIP Theme Frequency & Prevalence</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Empirical quantification of 29 canonical SIP research themes across verified Indian app review sampling frames.
            </p>
        </div>
    """, unsafe_allow_html=True)

    csv_path = "outputs/theme_frequencies.csv"
    if not os.path.exists(csv_path):
        engine = ThemeFrequencyEngine()
        df = engine.export_theme_frequencies(csv_path)
    else:
        df = pd.read_csv(csv_path)

    # Top KPI Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Themes Quantified", len(df))
    with col2:
        top_theme = df.iloc[0]
        st.metric("Top Recurring Theme", top_theme["theme_name"], f"{top_theme['prevalence_pct']}% Prev")
    with col3:
        validated_themes = (df["verification_status"] == "VALIDATED").sum()
        st.metric("Human-Validated Themes", f"{validated_themes} Themes", "High Confidence")
    with col4:
        eligible_denom = df.iloc[0]["eligible_denominator"]
        st.metric("Eligible Sampling Frame", f"{eligible_denom:,} Reviews", "8 Apps")

    st.markdown("---")

    # Filter controls
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        categories = ["All Categories"] + sorted(list(df["category"].unique()))
        sel_cat = st.selectbox("Filter by Theme Sub-Domain", options=categories)
    with col_f2:
        status_filter = st.radio("Verification Level", options=["All Themes", "Human-Validated Only", "Preliminary Only"], horizontal=True)

    filtered_df = df.copy()
    if sel_cat != "All Categories":
        filtered_df = filtered_df[filtered_df["category"] == sel_cat]
    if status_filter == "Human-Validated Only":
        filtered_df = filtered_df[filtered_df["verification_status"] == "VALIDATED"]
    elif status_filter == "Preliminary Only":
        filtered_df = filtered_df[filtered_df["verification_status"] == "PRELIMINARY"]

    st.subheader(f"Top Friction Themes ({len(filtered_df)} Matching)")
    
    # Bar chart of top themes in filtered view
    if not filtered_df.empty:
        chart_data = filtered_df.head(10).set_index("theme_name")["unique_reviews_with_theme"]
        st.bar_chart(chart_data)

    st.markdown("---")

    # Within-Frame Prevalence Comparison Table
    st.subheader("Within-Frame Cohort Prevalence (%)")
    st.caption("Prevalence is calculated strictly against each application's unique eligible review denominator.")

    display_cols = [
        "theme_name", "category", "unique_reviews_with_theme", "prevalence_pct",
        "verification_status", "groww_prevalence_pct", "zerodha_coin_prevalence_pct",
        "indmoney_prevalence_pct", "paytm_money_prevalence_pct", "et_money_prevalence_pct"
    ]
    renamed_cols = {
        "theme_name": "Theme",
        "category": "Domain",
        "unique_reviews_with_theme": "Reviews",
        "prevalence_pct": "Overall %",
        "verification_status": "Status",
        "groww_prevalence_pct": "Groww %",
        "zerodha_coin_prevalence_pct": "Coin %",
        "indmoney_prevalence_pct": "INDmoney %",
        "paytm_money_prevalence_pct": "Paytm %",
        "et_money_prevalence_pct": "ET Money %",
    }
    
    st.dataframe(filtered_df[display_cols].rename(columns=renamed_cols), use_container_width=True)

    # CSV Download
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Theme Prevalence Dataset (CSV)",
        data=csv,
        file_name="groww_sip_theme_frequencies.csv",
        mime="text/csv",
    )
