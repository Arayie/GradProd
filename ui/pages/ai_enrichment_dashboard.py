"""
AI Enrichment Dashboard
Provides holistic visibility into enrichment status, confidence distributions,
and language/application breakdowns.
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
from core.database_manager import get_database_manager

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Phase 4 Intelligence</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">AI Enrichment Dashboard</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Monitoring AI multi-label classification pipeline, confidence tiers, and human review routing.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    # Query key summary metrics
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
    total_eligible = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' AND ai_enrichment_status = 'ENRICHED'")
    total_enriched = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ai_evidence_log WHERE confidence_tier = 'LOW'")
    low_confidence = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ai_evidence_log WHERE routing_decision = 'MANDATORY_REVIEW'")
    mandatory_review = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM human_adjudications")
    total_adjudicated = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ai_evidence_log WHERE adjudication_status = 'ACCEPTED'")
    accepted_count = cursor.fetchone()[0]

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Eligible Records", f"{total_eligible:,}")
    with col2:
        st.metric("AI Enriched", f"{total_enriched:,}")
    with col3:
        st.metric("Mandatory Review", f"{mandatory_review:,}")
    with col4:
        st.metric("Low Confidence", f"{low_confidence:,}")
    with col5:
        st.metric("Human Adjudicated", f"{total_adjudicated:,}")

    st.markdown("---")

    # Visualizations: Confidence Tiers & Routing Decisions
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Confidence Tier Distribution")
        tier_df = pd.read_sql_query(
            "SELECT confidence_tier, COUNT(*) as count FROM ai_evidence_log GROUP BY confidence_tier", conn
        )
        if not tier_df.empty:
            st.bar_chart(tier_df.set_index("confidence_tier"))
        else:
            st.info("No AI enriched records in log.")

    with col_right:
        st.subheader("Human Routing Decisions")
        routing_df = pd.read_sql_query(
            "SELECT routing_decision, COUNT(*) as count FROM ai_evidence_log GROUP BY routing_decision", conn
        )
        if not routing_df.empty:
            st.bar_chart(routing_df.set_index("routing_decision"))
        else:
            st.info("No routing decisions logged.")

    st.markdown("---")

    # Breakdowns by App & Language
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Enrichments by Application")
        app_df = pd.read_sql_query(
            "SELECT app_name, COUNT(*) as count FROM ai_evidence_log GROUP BY app_name ORDER BY count DESC", conn
        )
        st.dataframe(app_df, use_container_width=True)

    with col_b:
        st.subheader("Grounding & Language Distribution")
        lang_df = pd.read_sql_query(
            """
            SELECT r.language_detected, e.evidence_grounding_status, COUNT(*) as count
            FROM ai_evidence_log e
            JOIN reviews r ON e.evidence_id = r.evidence_id
            GROUP BY r.language_detected, e.evidence_grounding_status
            """,
            conn,
        )
        st.dataframe(lang_df, use_container_width=True)

    conn.close()
