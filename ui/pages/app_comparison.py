"""
Cross-Application Competitor Comparison Dashboard (Page 8 - Phase 6)
Multi-dimensional benchmark comparing Groww against 7 leading peer applications.
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from analytics.benchmarking import CrossAppBenchmarkEngine
from core.database_manager import get_database_manager

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • App Comparison</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Cross-Platform Competitor Research</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Comparing Groww against peer Indian platforms across 11 core research friction dimensions.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="demo-banner">
            <strong>COMPARISON BOUNDARY:</strong> Store reviews reflect public feedback and relative friction signals, 
            not overall market share, financial stability, or total transactional volume.
        </div>
    """, unsafe_allow_html=True)

    tab_apple, tab_gplay = st.tabs(["Apple App Store India (Active)", "Google Play Store (Import Tracking)"])

    with tab_apple:
        csv_path = "outputs/cross_app_benchmarks.csv"
        if not os.path.exists(csv_path):
            engine = CrossAppBenchmarkEngine()
            df = engine.export_benchmarks(csv_path)
        else:
            df = pd.read_csv(csv_path)

        st.subheader("Platform Sentiment & Rating Distribution")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("**Average Star Rating (out of 5.0):**")
            st.bar_chart(df.set_index("app_name")["average_star_rating"])
        with col_c2:
            st.markdown("**1-Star Review Ratio (% of Corpus):**")
            st.bar_chart(df.set_index("app_name")["one_star_pct"])

        st.markdown("---")

        st.subheader("11-Dimension Friction & Benchmark Matrix")
        display_cols = [
            "app_name", "sampling_denominator", "average_star_rating", "one_star_pct",
            "mandate_friction_pct", "payment_friction_pct", "nav_reporting_friction_pct",
            "support_friction_pct", "cancellation_friction_pct", "rppi_payment", "competitive_position"
        ]
        renamed = {
            "app_name": "Application",
            "sampling_denominator": "Eligible Reviews",
            "average_star_rating": "Avg Rating",
            "one_star_pct": "1-Star %",
            "mandate_friction_pct": "Mandate %",
            "payment_friction_pct": "Payment %",
            "nav_reporting_friction_pct": "NAV %",
            "support_friction_pct": "Support %",
            "cancellation_friction_pct": "Cancel %",
            "rppi_payment": "Payment RPPI",
            "competitive_position": "Positioning",
        }
        st.dataframe(df[display_cols].rename(columns=renamed), use_container_width=True)

        st.markdown("---")
        st.subheader("Deep-Dive Application Inspection")
        sel_app_name = st.selectbox("Select Application to Inspect Detailed Metrics", options=df["app_name"].tolist())
        app_row = df[df["app_name"] == sel_app_name].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Eligible Sample Size", f"{app_row['sampling_denominator']:,} Reviews")
        with c2:
            st.metric("Average Rating", f"{app_row['average_star_rating']:.2f} ⭐")
        with c3:
            st.metric("Mandate Friction", f"{app_row['mandate_friction_pct']:.2f}%")
        with c4:
            st.metric("Payment RPPI", f"{app_row['rppi_payment']:.2f}", app_row["competitive_position"])

    with tab_gplay:
        st.subheader("Google Play Store Comparison Data")
        st.info("ℹ️ Google Play competitor data is currently operating on manual research imports. In compliance with data governance, automated scraping of competitor Play Store pages is disabled. Channels without verified manual imports are marked 'Unavailable' rather than displaying misleading zero values.")
        
        gplay_status = [
            {"Application": "Groww", "Google Play Package": "com.nextbillion.groww", "Data Status": "Unavailable (Awaiting Manual Import)", "Verified Reviews": "N/A"},
            {"Application": "Zerodha Coin", "Google Play Package": "com.zerodha.coin", "Data Status": "Unavailable (Awaiting Manual Import)", "Verified Reviews": "N/A"},
            {"Application": "INDmoney", "Google Play Package": "com.indwealth", "Data Status": "Unavailable (Awaiting Manual Import)", "Verified Reviews": "N/A"},
            {"Application": "Paytm Money", "Google Play Package": "com.paytmmoney", "Data Status": "Unavailable (Awaiting Manual Import)", "Verified Reviews": "N/A"},
        ]
        st.dataframe(pd.DataFrame(gplay_status), use_container_width=True)
