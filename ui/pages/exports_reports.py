"""
Exports and Research Reports Center (Phase 6 - Page 14)
Unified download portal for research datasets, executive PDF dossiers, and auditable analytics with strict RBAC enforcement.
"""

import streamlit as st
import pandas as pd
import os
import io
import sqlite3
from core.database_manager import get_database_manager
from core.auth import AuthService, Permission
from services.pdf_export_service import PDFExportService
from ui.navigation import render_header
from ui.brand import NAVY_CARD, NAVY_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, GROWW_GREEN

def render():
    render_header(
        "Exports and Research Reports",
        "Download standardized research datasets, executive PDF dossiers, and reproducible audit logs."
    )

    can_export_raw = AuthService.can_export_raw_data()
    can_export_reports = AuthService.can_export_reports()
    current_role = AuthService.get_current_role()

    # Role status card matching Groww dark fintech theme
    st.markdown(
        f'<div style="background-color: {NAVY_CARD}; border: 1px solid {NAVY_BORDER}; border-radius: 10px; padding: 0.9rem 1.2rem; margin-bottom: 1.25rem;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
        f'<div>'
        f'<span style="font-size: 0.75rem; font-weight: 700; color: {TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.05em;">Active Session Role</span>'
        f'<div style="font-size: 1.15rem; font-weight: 800; color: {GROWW_GREEN};">{current_role.value}</div>'
        f'</div>'
        f'<div style="text-align: right; font-size: 0.85rem; color: {TEXT_SECONDARY};">'
        f'<div>Raw Review Export: <strong style="color: {TEXT_PRIMARY};">{"ALLOWED" if can_export_raw else "RESTRICTED (Viewer Role)"}</strong></div>'
        f'<div>Executive Reports & Analytics: <strong style="color: {TEXT_PRIMARY};">{"ALLOWED" if can_export_reports else "RESTRICTED"}</strong></div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    tab_pdf, tab_analytics, tab_raw = st.tabs([
        "📄 Executive PDF Reports",
        "📊 Standardized Analytics Datasets (CSV)",
        "🔍 Research Review Evidence (CSV)"
    ])

    # 1. EXECUTIVE PDF REPORTS
    with tab_pdf:
        st.markdown("### Executive PDF Reports")
        st.markdown("Automated executive briefings and opportunity dossiers compiled using pure-Python PDF rendering.")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("""
                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;">
                    <h4 style="margin-top: 0; color: #0F172A;">Weekly Executive Discovery Digest</h4>
                    <p style="font-size: 0.9rem; color: #475569; line-height: 1.4;">
                        Executive summary covering weekly review collection volumes, sentiment benchmarks, top 3 SIP pain points, and strategic recommendations.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            pdf_digest_path = "outputs/weekly_discovery_digest.pdf"
            if not os.path.exists(pdf_digest_path):
                pdf_digest_path = PDFExportService.generate_weekly_digest(pdf_digest_path)

            if os.path.exists(pdf_digest_path):
                with open(pdf_digest_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="⬇️ Download Weekly Digest (PDF)",
                    data=pdf_bytes,
                    file_name="Groww_Weekly_Discovery_Digest.pdf",
                    mime="application/pdf",
                    key="dl_weekly_pdf"
                )

        with col_p2:
            st.markdown("""
                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;">
                    <h4 style="margin-top: 0; color: #0F172A;">Opportunity Prioritization Dossier</h4>
                    <p style="font-size: 0.9rem; color: #475569; line-height: 1.4;">
                        Detailed product dossier containing all 7 ranked opportunities, multi-factor scoring breakdowns, and recommended experiment interventions.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            pdf_opp_path = "outputs/opportunity_report.pdf"
            if not os.path.exists(pdf_opp_path):
                pdf_opp_path = PDFExportService.generate_opportunity_dossier(pdf_opp_path)

            if os.path.exists(pdf_opp_path):
                with open(pdf_opp_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="⬇️ Download Opportunity Dossier (PDF)",
                    data=pdf_bytes,
                    file_name="Groww_Ranked_Opportunities_Dossier.pdf",
                    mime="application/pdf",
                    key="dl_opp_pdf"
                )

    # 2. STANDARDIZED ANALYTICS DATASETS (CSV)
    with tab_analytics:
        st.markdown("### Standardized Analytics Exports")
        st.markdown("Reproducible quantitative datasets generated by Phase 5 discovery analytics engines.")

        analytics_files = [
            ("outputs/ranked_product_opportunities.csv", "Ranked Product Opportunities", "7 prioritized product intervention opportunities with multi-factor weights."),
            ("outputs/theme_frequencies.csv", "Theme Frequencies & Cross-App Prevalence", "29 canonical themes with prevalence across 8 apps and exact denominators."),
            ("outputs/lifecycle_journey_analytics.csv", "SIP Lifecycle Journey Analytics", "8 stages (S0-S7) with review counts, drop-off risks, and friction scores."),
            ("outputs/cross_app_benchmarks.csv", "Cross-App Comparative Benchmarks", "8 investment applications with RPPI metrics, rating distributions, and pain ratios."),
            ("outputs/sip_retention_hypotheses.csv", "12-Month SIP Retention Model Scenarios", "Simulation scenarios evaluating the compound retention leverage of interventions."),
            ("outputs/ai_evidence_log.csv", "AI Evidence & Audit Log", "Immutable audit trail of all AI enrichments, confidence tiers, and prompt hashes.")
        ]

        for file_path, name, desc in analytics_files:
            with st.container():
                c_info, c_btn = st.columns([3, 1])
                with c_info:
                    st.markdown(f"**{name}** (`{file_path}`)")
                    st.caption(desc)
                with c_btn:
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            csv_data = f.read()
                        st.download_button(
                            label=f"⬇️ CSV ({os.path.getsize(file_path) // 1024 + 1} KB)",
                            data=csv_data,
                            file_name=os.path.basename(file_path),
                            mime="text/csv",
                            key=f"dl_{os.path.basename(file_path)}"
                        )
                    else:
                        st.info("File not generated yet.")
                st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

    # 3. RESEARCH REVIEW EVIDENCE (CSV)
    with tab_raw:
        st.markdown("### Customer Review Evidence Export")
        st.markdown("Filtered review records with sanitized text and extracted metadata (PII-free).")

        if not can_export_raw:
            st.warning("⚠️ **Export Access Restricted:** The 'VIEWER' role is restricted from exporting raw customer review datasets to preserve data privacy. Only 'ADMIN', 'RESEARCHER', and 'AUDITOR' roles are authorized.")
        else:
            db_mgr = get_database_manager()
            conn = db_mgr.get_connection()

            # Filter options for export
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT app_name FROM reviews WHERE eligibility_status = 'ELIGIBLE'")
                eligible_apps = ["All Applications"] + [r[0] for r in cursor.fetchall()]
                sel_app = st.selectbox("Export Target App", options=eligible_apps)
            with f_col2:
                sel_cohort = st.selectbox("Review Cohort", options=["All Eligible Reviews", "SIP-Relevant Reviews Only"])

            # Query database
            query = """
            SELECT 
                evidence_id, app_name, store, star_rating, 
                review_created_at as review_date, review_text, language_detected, sip_relevance_status
            FROM reviews
            WHERE eligibility_status = 'ELIGIBLE'
            """
            params = []
            if sel_app != "All Applications":
                query += " AND app_name = ?"
                params.append(sel_app)
            if sel_cohort == "SIP-Relevant Reviews Only":
                query += " AND (sip_relevance_status = 'SIP_RELEVANT' OR mentions_sip = 1)"

            query += " ORDER BY review_created_at DESC"

            export_df = pd.read_sql_query(query, conn, params=params)
            conn.close()

            st.markdown(f"**Selected Dataset:** {len(export_df):,} review records")

            csv_buffer = io.StringIO()
            export_df.to_csv(csv_buffer, index=False)
            csv_str = csv_buffer.getvalue()

            st.download_button(
                label=f"⬇️ Export {len(export_df):,} Reviews (CSV)",
                data=csv_str,
                file_name=f"groww_evidence_{sel_app.replace(' ', '_')}_{sel_cohort.replace(' ', '_')}.csv",
                mime="text/csv",
                key="dl_raw_reviews"
            )
