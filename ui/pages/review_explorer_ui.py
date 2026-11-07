"""
Review Explorer and Evidence Inspector (Page 4 - Phase 6)
Full-text searchable, filterable, and paginated customer review browser with verbatim evidence inspection.
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import math
import html
from core.database_manager import get_database_manager
from core.auth import AuthService

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Review Explorer</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Research Review Explorer</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Browse, filter, and inspect canonical review records, exact verbatim evidence spans, and provenance metadata.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()
    cursor = conn.cursor()

    # Search & Filter Row 1
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        search_query = st.text_input("🔍 Full-Text Search in Reviews", placeholder="Search keywords (e.g., mandate, units, loss, SIP pause)...")
    with col_s2:
        cursor.execute("SELECT DISTINCT app_name FROM reviews WHERE eligibility_status = 'ELIGIBLE' ORDER BY app_name")
        apps = ["ALL"] + [r[0] for r in cursor.fetchall() if r[0]]
        sel_app = st.selectbox("Application", options=apps)
    with col_s3:
        sel_rating = st.selectbox("Star Rating", options=["ALL", "1 Star", "2 Stars", "3 Stars", "4 Stars", "5 Stars"])

    # Search & Filter Row 2
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        cursor.execute("SELECT DISTINCT language_detected FROM reviews WHERE eligibility_status = 'ELIGIBLE' ORDER BY language_detected")
        langs = ["ALL"] + [r[0] for r in cursor.fetchall() if r[0]]
        sel_lang = st.selectbox("Language Cohort", options=langs)
    with col_f2:
        cursor.execute("SELECT DISTINCT sip_relevance_status FROM reviews WHERE eligibility_status = 'ELIGIBLE' ORDER BY sip_relevance_status")
        rel_opts = ["ALL"] + [r[0] for r in cursor.fetchall() if r[0]]
        sel_rel = st.selectbox("SIP Relevance", options=rel_opts)
    with col_f3:
        cursor.execute("SELECT DISTINCT ai_lifecycle_stage FROM reviews WHERE ai_lifecycle_stage IS NOT NULL ORDER BY ai_lifecycle_stage")
        stages = ["ALL"] + [r[0] for r in cursor.fetchall() if r[0]]
        sel_stage = st.selectbox("Lifecycle Stage", options=stages)
    with col_f4:
        sel_val = st.selectbox("Validation Status", options=["ALL", "PENDING", "ACCEPTED", "CORRECTED", "REJECTED"])

    # Construct Filtered Query
    base_query = """
    FROM reviews r
    LEFT JOIN ai_evidence_log e ON r.evidence_id = e.evidence_id
    WHERE r.eligibility_status = 'ELIGIBLE'
    """
    params = []

    if search_query.strip():
        base_query += " AND (r.review_text LIKE ? OR r.review_title LIKE ?)"
        q = f"%{search_query.strip()}%"
        params.extend([q, q])

    if sel_app != "ALL":
        base_query += " AND r.app_name = ?"
        params.append(sel_app)

    if sel_rating != "ALL":
        star_val = int(sel_rating.split()[0])
        base_query += " AND r.star_rating = ?"
        params.append(star_val)

    if sel_lang != "ALL":
        base_query += " AND r.language_detected = ?"
        params.append(sel_lang)

    if sel_rel != "ALL":
        base_query += " AND r.sip_relevance_status = ?"
        params.append(sel_rel)

    if sel_stage != "ALL":
        base_query += " AND r.ai_lifecycle_stage = ?"
        params.append(sel_stage)

    if sel_val != "ALL":
        base_query += " AND r.ai_adjudication_status = ?"
        params.append(sel_val)

    # Count total matching
    count_cursor = conn.cursor()
    count_cursor.execute(f"SELECT COUNT(DISTINCT r.evidence_id) {base_query}", params)
    total_matches = count_cursor.fetchone()[0]

    st.markdown(f"**Found {total_matches:,} Matching Eligible Reviews**")

    # Export Button if Permitted
    if AuthService.can_export_raw_data() and total_matches > 0:
        export_query = f"""
        SELECT 
            r.evidence_id, r.app_name, r.store, r.star_rating, r.review_created_at,
            r.language_detected, r.sip_relevance_status, r.ai_lifecycle_stage,
            r.ai_primary_pain_point, r.ai_confidence_score, r.ai_adjudication_status,
            r.review_title, r.review_text
        {base_query}
        GROUP BY r.evidence_id
        ORDER BY r.review_created_at DESC
        LIMIT 1000
        """
        export_df = pd.read_sql_query(export_query, conn, params=params)
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered Reviews (CSV)",
            data=csv,
            file_name="groww_filtered_reviews_export.csv",
            mime="text/csv",
        )

    # Pagination
    page_size = 10
    total_pages = max(1, math.ceil(total_matches / page_size))
    col_p1, col_p2 = st.columns([1, 4])
    with col_p1:
        current_page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    with col_p2:
        st.write(f"Showing page {current_page} of {total_pages}")

    offset = (current_page - 1) * page_size

    # Fetch Page Records
    page_query = f"""
    SELECT 
        r.evidence_id, r.app_name, r.store, r.star_rating, r.review_created_at,
        r.app_version, r.language_detected, r.sip_relevance_status,
        r.review_title, r.review_text, r.review_text_original,
        r.ai_lifecycle_stage, r.ai_primary_pain_point, r.ai_confidence_score,
        r.ai_confidence_tier, r.ai_adjudication_status,
        e.evidence_spans, e.model_id, e.prompt_hash, e.taxonomy_version
    {base_query}
    GROUP BY r.evidence_id
    ORDER BY r.review_created_at DESC
    LIMIT {page_size} OFFSET {offset}
    """
    cursor.execute(page_query, params)
    page_records = cursor.fetchall()

    st.markdown("---")

    # Render Review Cards
    for row in page_records:
        r = dict(row)
        conf = r["ai_confidence_score"] or 0.0
        badge_color = "#10B981" if conf >= 0.80 else ("#F59E0B" if conf >= 0.65 else "#EF4444")
        safe_title = html.escape(str(r['review_title'])) if r['review_title'] else ""
        safe_text = html.escape(str(r['review_text'])) if r['review_text'] else ""
        title_prefix = f"<strong>{safe_title}</strong> - " if safe_title else ""

        with st.container():
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.1rem; margin-bottom: 0.9rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                        <div>
                            <span style="font-weight: 700; color: #0F172A; font-size: 1.05rem;">{r['app_name']}</span>
                            <span style="color: #64748B; font-size: 0.85rem; margin-left: 0.5rem;">
                                • {'⭐' * int(r['star_rating'])} • {str(r['review_created_at'])[:10]} • {r['language_detected']} • v{r['app_version'] or 'N/A'}
                            </span>
                        </div>
                        <div>
                            <span style="background-color: {badge_color}22; color: {badge_color}; padding: 0.2rem 0.55rem; border-radius: 12px; font-weight: 700; font-size: 0.78rem;">
                                {r['ai_confidence_tier'] or 'HIGH'} ({conf:.2f})
                            </span>
                            <span style="background-color: #E2E8F0; color: #334155; padding: 0.2rem 0.55rem; border-radius: 12px; font-weight: 600; font-size: 0.78rem; margin-left: 0.35rem;">
                                {r['ai_lifecycle_stage'] or 'STAGE_N/A'}
                            </span>
                        </div>
                    </div>
                    <div style="color: #1E293B; font-size: 0.95rem; line-height: 1.45; margin-bottom: 0.5rem;">
                        {title_prefix}{safe_text}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            with st.expander(f"Inspect Complete Evidence & Provenance [{r['evidence_id']}]"):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown("**Taxonomy Classifications:**")
                    st.write(f"- Primary Pain Point: `{r['ai_primary_pain_point']}`")
                    st.write(f"- SIP Relevance: `{r['sip_relevance_status']}`")
                    st.write(f"- Adjudication Status: `{r['ai_adjudication_status']}`")
                    if r["evidence_spans"]:
                        try:
                            spans = json.loads(r["evidence_spans"])
                            st.markdown("**Verbatim Substring Evidence:**")
                            for lbl, sp in spans.items():
                                if sp:
                                    st.info(f"📌 *\"{sp}\"* ({lbl})")
                        except Exception:
                            pass
                with col_d2:
                    st.markdown("**Audit Provenance Metadata:**")
                    st.write(f"- Evidence ID: `{r['evidence_id']}`")
                    st.write(f"- Model Identifier: `{r['model_id'] or 'rule-nlp-v2.0'}`")
                    st.write(f"- Prompt Hash: `{r['prompt_hash'] or 'N/A'}`")
                    st.write(f"- Taxonomy Version: `{r['taxonomy_version'] or '2.0.0'}`")
                    st.write(f"- Retention Policy: `365 Days Active`")

    conn.close()
