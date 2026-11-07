"""
SIP Pain Point Explorer
The primary qualitative discovery interface for exploring verified investor pain points,
verbatim evidence spans, and cross-application failure modes.
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
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • SIP Pain-Point Explorer</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">SIP Pain-Point Discovery</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Explore granular friction points with 100% exact verbatim evidence spans grounded in genuine customer reviews.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    # Query filter options
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT app_name FROM ai_evidence_log WHERE app_name IS NOT NULL ORDER BY app_name")
    apps = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT lifecycle_stage FROM ai_evidence_log WHERE lifecycle_stage IS NOT NULL ORDER BY lifecycle_stage")
    stages = [r[0] for r in cursor.fetchall()]

    # Filter sidebar / top row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sel_app = st.selectbox("Target Application", options=["All Applications"] + apps)
    with col2:
        sel_stage = st.selectbox("SIP Lifecycle Stage", options=["All Lifecycle Stages"] + stages)
    with col3:
        sel_lang = st.selectbox("Language Filter", options=["All Languages", "English Only", "Hindi / Hinglish Only"])
    with col4:
        min_conf = st.slider("Minimum Confidence", min_value=0.50, max_value=1.00, value=0.70, step=0.05)

    # Build SQL Query
    query = """
    SELECT 
        e.evidence_id, e.app_name, e.lifecycle_stage, e.pain_points,
        e.evidence_spans, e.confidence_overall, e.confidence_tier,
        e.routing_decision, e.evidence_grounding_status, e.adjudication_status,
        e.reasoning_summary, r.review_text, r.star_rating, r.language_detected,
        r.review_created_at, r.sip_relevance_status
    FROM ai_evidence_log e
    JOIN reviews r ON e.evidence_id = r.evidence_id
    WHERE e.confidence_overall >= ?
    """
    params = [min_conf]

    if sel_app != "All Applications":
        query += " AND e.app_name = ?"
        params.append(sel_app)

    if sel_stage != "All Lifecycle Stages":
        query += " AND e.lifecycle_stage = ?"
        params.append(sel_stage)

    if sel_lang == "English Only":
        query += " AND r.language_detected = 'en'"
    elif sel_lang == "Hindi / Hinglish Only":
        query += " AND r.language_detected IN ('hi', 'hi-Latn', 'mixed')"

    query += " ORDER BY e.confidence_overall DESC LIMIT 100"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    st.markdown(f"**Showing {len(df)} matching investor feedback records**")

    if df.empty:
        st.info("No records match the current filter criteria. Try adjusting filters.")
        return

    # Pain-point summary pills
    all_pains = []
    for p_str in df["pain_points"].dropna():
        try:
            p_list = json.loads(p_str)
            all_pains.extend(p_list)
        except Exception:
            pass

    pain_counts = pd.Series(all_pains).value_counts()
    st.markdown("### Top Detected Pain Points in Filtered Selection")
    st.bar_chart(pain_counts.head(8))

    st.markdown("---")
    st.markdown("### Granular Evidence Feed")

    for _, row in df.iterrows():
        pains = json.loads(row["pain_points"]) if row["pain_points"] else []
        spans = json.loads(row["evidence_spans"]) if row["evidence_spans"] else {}

        # Determine color for confidence badge
        conf = row["confidence_overall"]
        badge_color = "#10B981" if conf >= 0.80 else ("#F59E0B" if conf >= 0.65 else "#EF4444")

        with st.container():
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <span style="font-weight: 700; color: #1E293B; font-size: 1.05rem;">{row['app_name']}</span>
                            <span style="color: #64748B; font-size: 0.85rem; margin-left: 0.5rem;">• {'⭐' * int(row['star_rating'])} • {str(row['review_created_at'])[:10]} • {row['language_detected']}</span>
                        </div>
                        <div>
                            <span style="background-color: {badge_color}22; color: {badge_color}; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.80rem; font-weight: 700;">
                                {row['confidence_tier']} ({conf:.2f})
                            </span>
                            <span style="background-color: #E2E8F0; color: #334155; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.80rem; font-weight: 600; margin-left: 0.4rem;">
                                {row['lifecycle_stage']}
                            </span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Display exact verbatim spans
            if spans:
                st.markdown("**Exact Grounded Evidence Spans:**")
                for label, span_text in spans.items():
                    if span_text:
                        st.info(f"📌 **{label}**: *\"{span_text}\"*")

            with st.expander(f"Full Review Text ({row['evidence_id']})"):
                st.write(row["review_text"])
                st.caption(f"Relevance: {row['sip_relevance_status']} | Adjudication: {row['adjudication_status']} | Routing: {row['routing_decision']}")
