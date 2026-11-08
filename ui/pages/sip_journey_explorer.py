"""
SIP Journey Explorer (Page 5 - Phase 6)
Visual exploration across 8 SIP Lifecycle Stages with supporting evidence and counter-evidence.
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from core.database_manager import get_database_manager
from ui.navigation import render_header

LIFECYCLE_STAGES = [
    ("S0_DISCOVERY", "S0 Discovery & Evaluation", "Exploring funds, app onboarding, comparing peers, beginner questions."),
    ("S1_SETUP", "S1 Setup & Mandate", "Bank e-mandate registration, UPI Autopay setup, KYC verification."),
    ("S2_EARLY", "S2 Early Instalments", "First debit execution, waiting for unit allotment, transaction status confusion."),
    ("S3_HABIT", "S3 Habitual Investing", "Ongoing recurring monthly debits, long-term habit formation, routine monitoring."),
    ("S4_REVIEW", "S4 Expansion & Step-Up", "Increasing SIP amount, step-up SIP setup, portfolio diversification, multi-fund management."),
    ("S5_FRICTION", "S5 Friction & Modification", "Payment failures, date change difficulty, pause friction, unhelpful support loops."),
    ("S6_PAUSE_STOP", "S6 Cancellation & Stop", "Stopping SIP, cancelling mandate, fund redemption, terminal platform exit."),
    ("S7_RESTART", "S7 Resumption & Restart", "Resuming paused SIP, restarting after break, re-activating investment habit."),
]

def render():
    render_header(
        "8-Stage SIP Lifecycle Journey",
        "Longitudinal analysis of customer friction, behaviours, triggers, and outcomes across the complete SIP lifecycle."
    )

    st.markdown(
        '<div class="demo-banner">'
        '<strong>LONGITUDINAL RESEARCH BOUNDARY:</strong> Customer app reviews represent independent public signals from different users. '
        'They are categorized into contextual lifecycle stages based on explicit text evidence, not audited account ledgers.'
        '</div>',
        unsafe_allow_html=True
    )

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()
    cursor = conn.cursor()

    # Query counts per stage
    cursor.execute("SELECT lifecycle_stage, COUNT(*) FROM ai_evidence_log GROUP BY lifecycle_stage")
    stage_counts = dict(cursor.fetchall())

    # Stage selector tabs
    stage_labels = [f"{s[1]} ({stage_counts.get(s[0], 0)})" for s in LIFECYCLE_STAGES]
    selected_idx = st.selectbox("Select Lifecycle Stage to Inspect", options=range(len(LIFECYCLE_STAGES)), format_func=lambda i: stage_labels[i])

    code, name, desc = LIFECYCLE_STAGES[selected_idx]
    review_count = stage_counts.get(code, 0)

    # Top KPI cards for selected stage
    st.subheader(name)
    st.info(f"**Stage Focus:** {desc}")

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Total Identified Reviews", f"{review_count:,}")

    query = """
    SELECT 
        e.evidence_id, e.app_name, e.investor_intent, e.expectations,
        e.behaviour, e.pain_points, e.triggers, e.outside_app_actions,
        e.reported_outcome, e.evidence_spans, e.confidence_overall,
        r.star_rating, r.review_text, r.review_created_at
    FROM ai_evidence_log e
    JOIN reviews r ON e.evidence_id = r.evidence_id
    WHERE e.lifecycle_stage = ?
    ORDER BY e.confidence_overall DESC LIMIT 50
    """
    df = pd.read_sql_query(query, conn, params=[code])
    conn.close()

    with k2:
        avg_rating = round(df["star_rating"].mean(), 2) if not df.empty else 0.0
        st.metric("Average Star Rating", f"{avg_rating:.2f} ⭐" if avg_rating else "N/A")

    with k3:
        avg_conf = round(df["confidence_overall"].mean(), 2) if not df.empty else 0.0
        st.metric("Mean AI Confidence", f"{avg_conf:.2f}" if avg_conf else "N/A")

    st.markdown("---")

    if df.empty:
        st.warning(f"No customer reviews currently classified under {name} in the research corpus.")
        return

    # Visualizations: Pain Points and Behaviours
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.subheader("Common Pain Points in this Stage")
        stage_pains = []
        for p in df["pain_points"].dropna():
            try:
                stage_pains.extend(json.loads(p))
            except Exception:
                pass
        filtered_pains = [p for p in stage_pains if p != "NO_PAIN_POINT_STATED"]
        if filtered_pains:
            st.bar_chart(pd.Series(filtered_pains).value_counts().head(6))
        else:
            st.write("Predominantly positive feedback with zero friction reported.")

    with col_v2:
        st.subheader("Reported Investor Behaviours")
        stage_behaviours = []
        for b in df["behaviour"].dropna():
            try:
                stage_behaviours.extend(json.loads(b))
            except Exception:
                pass
        filtered_beh = [b for b in stage_behaviours if b != "NOT_STATED"]
        if filtered_beh:
            st.bar_chart(pd.Series(filtered_beh).value_counts().head(6))
        else:
            st.write("No distinct behaviours reported.")

    st.markdown("---")

    # Supporting Evidence and Counter-Evidence Columns
    st.subheader(f"Qualitative Evidence & Counter-Evidence: {name}")
    col_supp, col_count = st.columns(2)

    with col_supp:
        st.markdown("### Supporting Evidence (Friction Points)")
        friction_reviews = df[df["star_rating"] <= 3].head(4)
        if not friction_reviews.empty:
            for _, r in friction_reviews.iterrows():
                spans = json.loads(r["evidence_spans"]) if r["evidence_spans"] else {}
                with st.container():
                    st.markdown(f"**{r['app_name']}** • ⭐ {r['star_rating']}")
                    st.write(f"\"{r['review_text']}\"")
                    if spans:
                        for lbl, sp in spans.items():
                            if sp:
                                st.info(f"📌 *\"{sp}\"* ({lbl})")
                    st.divider()
        else:
            st.write("No friction reviews found in this stage.")

    with col_count:
        st.markdown("### Counter-Evidence (Satisfied / Smooth Habit)")
        positive_reviews = df[df["star_rating"] >= 4].head(4)
        if not positive_reviews.empty:
            for _, r in positive_reviews.iterrows():
                with st.container():
                    st.markdown(f"**{r['app_name']}** • ⭐ {r['star_rating']}")
                    st.success(f"\"{r['review_text']}\"")
                    st.caption(f"Outcome: {r['reported_outcome']}")
                    st.divider()
        else:
            st.write("No counter-evidence reviews found in this stage.")
