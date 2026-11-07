"""
AI Evidence Log & Audit Trail
Searchable, reproducible record of all AI enrichments, model hashes, and verbatim spans.
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
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Audit Trail</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">AI Evidence Log & Audit Trail</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Immutable, reproducible audit trail linking classifications, prompt hashes, and verbatim evidence spans.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_tier = st.selectbox("Confidence Tier", options=["All Tiers", "HIGH", "MEDIUM", "LOW"])
    with col2:
        f_routing = st.selectbox("Routing Decision", options=["All Decisions", "AUTO_PUBLISH", "SAMPLE_AUDIT", "MANDATORY_REVIEW"])
    with col3:
        f_adjudication = st.selectbox("Adjudication Status", options=["All Statuses", "PENDING", "ACCEPTED", "CORRECTED", "REJECTED"])
    with col4:
        f_search = st.text_input("Search Review / Evidence ID", placeholder="e.g. EV_GROWW_ or mandate...")

    query = """
    SELECT 
        e.enrichment_id, e.evidence_id, e.app_name, e.lifecycle_stage,
        e.confidence_overall, e.confidence_tier, e.routing_decision,
        e.evidence_grounding_status, e.adjudication_status, e.model_provider,
        e.model_id, e.prompt_hash, e.taxonomy_version, e.classification_timestamp,
        r.review_text
    FROM ai_evidence_log e
    JOIN reviews r ON e.evidence_id = r.evidence_id
    WHERE 1=1
    """
    params = []

    if f_tier != "All Tiers":
        query += " AND e.confidence_tier = ?"
        params.append(f_tier)
    if f_routing != "All Decisions":
        query += " AND e.routing_decision = ?"
        params.append(f_routing)
    if f_adjudication != "All Statuses":
        query += " AND e.adjudication_status = ?"
        params.append(f_adjudication)
    if f_search.strip():
        query += " AND (e.evidence_id LIKE ? OR r.review_text LIKE ?)"
        term = f"%{f_search.strip()}%"
        params.extend([term, term])

    query += " ORDER BY e.classification_timestamp DESC LIMIT 100"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    st.markdown(f"**Found {len(df)} matching log entries**")

    # CSV Download button
    if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Log as CSV",
            data=csv,
            file_name="groww_ai_evidence_log_export.csv",
            mime="text/csv",
        )

    # Display grid
    display_cols = [
        "evidence_id", "app_name", "lifecycle_stage", "confidence_overall",
        "confidence_tier", "routing_decision", "adjudication_status", "model_id", "prompt_hash"
    ]
    st.dataframe(df[display_cols] if not df.empty else df, use_container_width=True)

    if not df.empty:
        st.markdown("### Inspect Record Audit Details")
        selected_ev_id = st.selectbox("Select Evidence ID to inspect", options=df["evidence_id"].tolist())
        selected_record = df[df["evidence_id"] == selected_ev_id].iloc[0]

        with st.container():
            st.write(f"**Review Text:** \"{selected_record['review_text']}\"")
            st.json({
                "enrichment_id": selected_record["enrichment_id"],
                "evidence_id": selected_record["evidence_id"],
                "model_provider": selected_record["model_provider"],
                "model_id": selected_record["model_id"],
                "prompt_hash": selected_record["prompt_hash"],
                "taxonomy_version": selected_record["taxonomy_version"],
                "timestamp": str(selected_record["classification_timestamp"]),
            })
