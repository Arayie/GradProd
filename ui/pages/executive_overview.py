"""
Executive Overview Dashboard (Page 1 - Phase 6)
High-level executive landing page providing dataset health, coverage, top pain points,
journey overview, opportunity summary, and research governance warnings.
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from core.database_manager import get_database_manager
from core.auth import AuthService

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Executive Overview</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Executive Research Dashboard</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Independent qualitative intelligence synthesized from 3,790 verified customer reviews across top Indian investment platforms.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()
    cursor = conn.cursor()

    # Query Section A: Dataset Health
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_stored = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
    total_eligible = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND sip_relevance_status IN ('DIRECT_SIP_RELEVANT', 'INDIRECT_SIP_RELEVANT')")
    sip_relevant = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM human_adjudications")
    total_adj = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ai_evidence_log WHERE adjudication_status = 'PENDING'")
    pending_adj = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'SYNTHETIC_DEMO'")
    blocked_count = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(review_created_at), MIN(review_created_at) FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
    date_range = cursor.fetchone()
    latest_date = str(date_range[0])[:10] if date_range[0] else "N/A"
    earliest_date = str(date_range[1])[:10] if date_range[1] else "N/A"

    cursor.execute("SELECT AVG(data_quality_score) FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
    avg_quality = cursor.fetchone()[0] or 1.0

    # Render KPI Cards
    st.subheader("Dataset Health & Integrity")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Eligible Research Reviews", f"{total_eligible:,}", f"Stored: {total_stored:,}")
    with kpi2:
        st.metric("SIP-Relevant Reviews", f"{sip_relevant:,}", "High-Signal Journey Evidence")
    with kpi3:
        st.metric("Human-Validated Reviews", f"{total_adj:,}", f"Pending: {pending_adj:,}")
    with kpi4:
        st.metric("Data Quality Score", f"{avg_quality:.2f} / 1.0", f"Blocked Demo: {blocked_count}")

    st.markdown("---")

    # Section B: Research Coverage
    st.subheader("Research Coverage & Store Provenance")
    cov1, cov2, cov3, cov4 = st.columns(4)
    with cov1:
        cursor.execute("SELECT COUNT(DISTINCT app_id) FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
        apps_covered = cursor.fetchone()[0]
        st.metric("Applications Covered", f"{apps_covered} Platforms", "Groww + 7 Peers")
    with cov2:
        st.metric("Apple App Store Reviews", f"{total_eligible:,}", "India Storefront (IN)")
    with cov3:
        st.metric("Google Play Status", "Manual CSV Ready", "Zero Unapproved Scraping")
    with cov4:
        st.metric("Review Date Window", f"{latest_date}", f"From: {earliest_date}")

    st.markdown("---")

    # Section C: Top Recurring SIP Pain Points
    st.subheader("Top Validated SIP Friction Themes")
    st.caption("Empirical prevalence calculated strictly against the 3,790 eligible review sampling frame.")

    theme_csv = "outputs/theme_frequencies.csv"
    if os.path.exists(theme_csv):
        df_themes = pd.read_csv(theme_csv)
        top_themes = df_themes.head(6)[
            ["theme_name", "category", "unique_reviews_with_theme", "prevalence_pct", "verification_status", "groww_prevalence_pct"]
        ].rename(columns={
            "theme_name": "Theme",
            "category": "Sub-Domain",
            "unique_reviews_with_theme": "Reviews",
            "prevalence_pct": "Prevalence %",
            "verification_status": "Status",
            "groww_prevalence_pct": "Groww Prev %",
        })
        st.dataframe(top_themes, use_container_width=True)
    else:
        st.info("Theme frequency dataset generating...")

    st.markdown("---")

    # Section D: SIP Journey Overview (Clickable 8 Stages)
    st.subheader("8-Stage SIP Lifecycle Journey")
    st.write("Click any stage to view active friction and customer feedback volume:")

    stages = [
        ("S0", "S0 Discovery", "Exploring funds, app onboarding, comparing peers"),
        ("S1", "S1 Setup & Mandate", "Bank e-mandate registration, UPI autopay, KYC verification"),
        ("S2", "S2 Early Instalments", "First debit execution, waiting for unit allotment"),
        ("S3", "S3 Habitual Investing", "Ongoing recurring monthly debits, long-term habit"),
        ("S4", "S4 Expansion & Step-Up", "Increasing SIP amount, portfolio diversification"),
        ("S5", "S5 Friction & Mod", "Payment failures, date change difficulty, pause friction"),
        ("S6", "S6 Cancellation & Stop", "Stopping SIP, cancelling mandate, fund redemption"),
        ("S7", "S7 Resumption & Restart", "Resuming paused SIP, restarting after break"),
    ]

    cursor.execute("SELECT lifecycle_stage, COUNT(*) FROM ai_evidence_log GROUP BY lifecycle_stage")
    stage_counts = dict(cursor.fetchall())

    cols_st1 = st.columns(4)
    for idx, (code_prefix, s_name, s_desc) in enumerate(stages[:4]):
        with cols_st1[idx]:
            count = stage_counts.get(s_name.split()[0], 0)
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                    <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">{s_name}</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #1E3A2F; margin: 0.25rem 0;">{count:,} Reviews</div>
                    <div style="color: #64748B; font-size: 0.80rem;">{s_desc}</div>
                </div>
            """, unsafe_allow_html=True)

    cols_st2 = st.columns(4)
    for idx, (code_prefix, s_name, s_desc) in enumerate(stages[4:]):
        with cols_st2[idx]:
            count = stage_counts.get(s_name.split()[0], 0)
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;">
                    <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">{s_name}</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #1E3A2F; margin: 0.25rem 0;">{count:,} Reviews</div>
                    <div style="color: #64748B; font-size: 0.80rem;">{s_desc}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Section E: Opportunity Summary
    st.subheader("Prioritized Product Opportunities")
    opp_csv = "outputs/ranked_product_opportunities.csv"
    if os.path.exists(opp_csv):
        df_opp = pd.read_csv(opp_csv).head(4)
        for _, opp in df_opp.iterrows():
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border-left: 4px solid #00D09C; border: 1px solid #CBD5E1; border-radius: 6px; padding: 0.85rem 1.1rem; margin-bottom: 0.6rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 700; color: #0F172A;">#{opp.get('priority_rank', '')} [{opp.get('opportunity_id', '')}] {opp.get('title', opp.get('opportunity_title', 'Opportunity'))}</span>
                        <span style="background-color: #00D09C22; color: #065F46; padding: 0.15rem 0.5rem; border-radius: 10px; font-weight: 700; font-size: 0.82rem;">Score: {float(opp.get('opportunity_score', 0)):.2f}</span>
                    </div>
                    <div style="color: #475569; font-size: 0.88rem; margin-top: 0.35rem;">{opp['problem_statement'][:130]}...</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Section F: Research Governance Warnings
    st.subheader("Research Governance Invariants & Limitations")
    st.markdown("""
        <div class="demo-banner">
            <strong>RESEARCH LIMITATIONS & COMPLIANCE BOUNDARIES:</strong><br/>
            • <strong>Rolling Velocity Discrepancy:</strong> High review velocity on Groww limits the 500-review RSS feed to a ~63-day rolling window, whereas Zerodha Coin spans 6.5 years.<br/>
            • <strong>No Internal Telemetry:</strong> Public store reviews reflect discovery signals and customer sentiment, not verified internal retention ledgers or CRM accounts.<br/>
            • <strong>Zero Scraped Endpoints:</strong> Google Play data operates on approved manual imports; no unauthorized HTML scraping is executed.
        </div>
    """, unsafe_allow_html=True)

    conn.close()
