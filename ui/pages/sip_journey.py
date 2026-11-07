"""
SIP Journey Explorer
Presents structured investor intelligence across the 8 Mutual Fund SIP Lifecycle Stages.
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
from core.database_manager import get_database_manager

LIFECYCLE_STAGES = [
    ("S0_DISCOVERY", "S0 Discovery", "Exploring funds, opening account, onboarding, comparing platforms."),
    ("S1_SETUP", "S1 Setup & Mandate", "Setting up first SIP, bank mandate registration, UPI autopay, KYC verification."),
    ("S2_EARLY", "S2 First Payment", "Initial instalment debit, waiting for unit allotment, early NAV verification."),
    ("S3_HABIT", "S3 Habitual Investing", "Ongoing monthly recurring debits, habitual tracking, long-term portfolio accumulation."),
    ("S4_REVIEW", "S4 Expansion & Review", "Increasing SIP amount, step-up SIP setup, portfolio diversification, adding new AMC funds."),
    ("S5_FRICTION", "S5 Friction & Modification", "Payment failures, date modification, attempting to pause SIP, skipping instalments."),
    ("S6_PAUSE_STOP", "S6 Stop & Cancellation", "Stopping SIP, cancelling autopay mandate, redeeming funds, switching platforms."),
    ("S7_RESTART", "S7 Resumption & Restart", "Resuming paused SIP, starting new investment cycle after previous cancellation."),
]

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • SIP Journey Explorer</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">8-Stage SIP Lifecycle Journey</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Longitudinal analysis of customer friction, motivations, and behaviours across the complete SIP lifecycle.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    # Query stage counts
    cursor = conn.cursor()
    cursor.execute("SELECT lifecycle_stage, COUNT(*) FROM ai_evidence_log GROUP BY lifecycle_stage")
    stage_counts = dict(cursor.fetchall())

    # Stage navigation tabs
    stage_labels = [f"{s[1]} ({stage_counts.get(s[0], 0)})" for s in LIFECYCLE_STAGES]
    selected_tab = st.selectbox("Select Lifecycle Stage to Inspect", options=range(len(LIFECYCLE_STAGES)), format_func=lambda i: stage_labels[i])

    code, name, desc = LIFECYCLE_STAGES[selected_tab]
    count = stage_counts.get(code, 0)

    st.markdown(f"### {name}")
    st.info(f"**Stage Definition:** {desc}")

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total Identified Reviews", f"{count:,}")

    # Query records for this stage
    query = """
    SELECT 
        e.evidence_id, e.app_name, e.investor_intent, e.expectations,
        e.behaviour, e.pain_points, e.triggers, e.outside_app_actions,
        e.reported_outcome, e.evidence_spans, e.confidence_overall,
        r.review_text, r.star_rating, r.review_created_at
    FROM ai_evidence_log e
    JOIN reviews r ON e.evidence_id = r.evidence_id
    WHERE e.lifecycle_stage = ?
    ORDER BY e.confidence_overall DESC LIMIT 30
    """
    df = pd.read_sql_query(query, conn, params=[code])
    conn.close()

    with col_m2:
        avg_star = df["star_rating"].mean() if not df.empty else 0.0
        st.metric("Average Star Rating", f"{avg_star:.1f} / 5.0" if avg_star else "N/A")

    with col_m3:
        avg_conf = df["confidence_overall"].mean() if not df.empty else 0.0
        st.metric("Average AI Confidence", f"{avg_conf:.2f}" if avg_conf else "N/A")

    st.markdown("---")

    if df.empty:
        st.warning(f"No customer reviews currently classified under {name} in the research corpus.")
        return

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Common Pain Points in this Stage")
        stage_pains = []
        for p in df["pain_points"].dropna():
            try:
                stage_pains.extend(json.loads(p))
            except Exception:
                pass
        if stage_pains:
            st.bar_chart(pd.Series(stage_pains).value_counts().head(5))
        else:
            st.write("No distinct pain points logged.")

    with col_right:
        st.subheader("Key Investor Behaviours")
        stage_behaviours = []
        for b in df["behaviour"].dropna():
            try:
                stage_behaviours.extend(json.loads(b))
            except Exception:
                pass
        if stage_behaviours:
            st.bar_chart(pd.Series(stage_behaviours).value_counts().head(5))
        else:
            st.write("No distinct behaviours logged.")

    st.markdown("---")
    st.subheader(f"Exemplar Verbatim Feedback for {name}")

    for _, row in df.head(6).iterrows():
        spans = json.loads(row["evidence_spans"]) if row["evidence_spans"] else {}
        with st.expander(f"{row['app_name']} • ⭐ {row['star_rating']} • {str(row['review_created_at'])[:10]}"):
            st.write(f"**Review:** \"{row['review_text']}\"")
            if spans:
                for lbl, sp in spans.items():
                    if sp:
                        st.markdown(f"🔍 **{lbl}**: *\"{sp}\"*")
            st.caption(f"Evidence ID: {row['evidence_id']} | Outcome: {row['reported_outcome']}")
