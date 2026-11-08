"""
Opportunity Radar & Strategic Prioritization Matrix (Phase 6 - Page 9)
High-level strategic opportunity exploration, multi-factor scoring breakdown, and discovery backlog.
"""

import streamlit as st
import pandas as pd
import altair as alt
import os
from services.opportunity_service import OpportunityService
from core.auth import AuthService, Permission
from ui.navigation import render_header

def render():
    render_header(
        "Opportunity Radar",
        "Strategic prioritization matrix scoring high-leverage product interventions across SIP lifecycle stages."
    )

    service = OpportunityService()
    opportunities = service.get_all_opportunities()
    if not opportunities:
        st.warning("No opportunities found in discovery database.")
        return

    df = pd.DataFrame(opportunities)

    # Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Scored Opportunities", len(df))
    with col2:
        top_opp = df.iloc[0]
        st.metric("Top Ranked Opportunity", top_opp["opportunity_id"], f"Score: {top_opp['opportunity_score']:.2f} / 10")
    with col3:
        st.metric("Top Leverage Stage", top_opp["lifecycle_stage"])
    with col4:
        active_count = len(df[df["lifecycle_status"].isin(["READY_FOR_EXPERIMENT", "IN_PROGRESS", "VALIDATED"])])
        st.metric("Active Pipeline", f"{active_count} of {len(df)}")

    st.markdown("---")

    # Filters Section
    st.markdown("### Strategic Opportunity Filters")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        stages = ["ALL"] + sorted(df["lifecycle_stage"].dropna().unique().tolist())
        sel_stage = st.selectbox("Filter Lifecycle Stage", options=stages)
    with f_col2:
        apps = ["ALL"] + sorted(df["target_application"].dropna().unique().tolist())
        sel_app = st.selectbox("Filter Target Application", options=apps)
    with f_col3:
        statuses = ["ALL"] + sorted(df["lifecycle_status"].dropna().unique().tolist())
        sel_status = st.selectbox("Filter Status", options=statuses)
    with f_col4:
        search_query = st.text_input("Search Opportunities", placeholder="e.g. mandate, NAV, pause...")

    filtered_df = df.copy()
    if sel_stage != "ALL":
        filtered_df = filtered_df[filtered_df["lifecycle_stage"] == sel_stage]
    if sel_app != "ALL":
        filtered_df = filtered_df[filtered_df["target_application"] == sel_app]
    if sel_status != "ALL":
        filtered_df = filtered_df[filtered_df["lifecycle_status"] == sel_status]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_df = filtered_df[
            filtered_df["title"].str.lower().str.contains(q) |
            filtered_df["problem_statement"].str.lower().str.contains(q) |
            filtered_df["opportunity_id"].str.lower().str.contains(q)
        ]

    # Prioritization Leaderboard
    st.markdown("### Opportunity Prioritization Leaderboard")
    display_cols = [
        "priority_rank", "opportunity_id", "title", "lifecycle_stage", 
        "opportunity_score", "lifecycle_status", "target_application"
    ]
    st.dataframe(
        filtered_df[display_cols].rename(columns={
            "priority_rank": "Rank",
            "opportunity_id": "ID",
            "title": "Opportunity Title",
            "lifecycle_stage": "Stage",
            "opportunity_score": "Score (10)",
            "lifecycle_status": "Status",
            "target_application": "App Context"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # Interactive 2D Strategic Matrix Chart
    st.markdown("### 2D Strategic Opportunity Matrix")
    st.caption("Visualizing Severity vs Actionability with bubble size proportional to Prevalence")

    chart = alt.Chart(df).mark_circle(size=260).encode(
        x=alt.X("actionability_score:Q", title="Actionability (Engineering / Product Feasibility 1-10)", scale=alt.Scale(domain=[0, 10])),
        y=alt.Y("severity_score:Q", title="Customer Severity Score (Friction Severity 1-10)", scale=alt.Scale(domain=[0, 10])),
        color=alt.Color("lifecycle_stage:N", title="Lifecycle Stage", scale=alt.Scale(scheme="category10")),
        size=alt.Size("prevalence_score:Q", title="Prevalence Score", scale=alt.Scale(range=[100, 600])),
        tooltip=["opportunity_id:N", "title:N", "opportunity_score:Q", "lifecycle_stage:N", "lifecycle_status:N"]
    ).properties(height=380).interactive()

    text_labels = chart.mark_text(
        align="left",
        baseline="middle",
        dx=14,
        fontSize=11,
        fontWeight="bold"
    ).encode(
        text="opportunity_id:N"
    )

    st.altair_chart(chart + text_labels, use_container_width=True)

    st.markdown("---")

    # Opportunity Cards & Quick Action to Dossier
    st.markdown("### Opportunity Cards")
    for _, row in filtered_df.iterrows():
        opp_id = row["opportunity_id"]
        score = row["opportunity_score"]
        status = row["lifecycle_status"]

        status_colors = {
            "DISCOVERED": "#3B82F6",
            "NEEDS_VALIDATION": "#F59E0B",
            "READY_FOR_EXPERIMENT": "#10B981",
            "IN_PROGRESS": "#8B5CF6",
            "VALIDATED": "#059669",
            "REJECTED": "#EF4444",
            "ON_HOLD": "#6B7280"
        }
        color = status_colors.get(status, "#6B7280")

        with st.container():
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                        <h4 style="margin: 0; color: #0F172A; font-size: 1.15rem; font-weight: 700;">
                            #{row['priority_rank']} [{opp_id}] {row['title']}
                        </h4>
                        <div>
                            <span style="background-color: #F1F5F9; color: #0F172A; font-weight: 700; padding: 0.3rem 0.6rem; border-radius: 6px; font-size: 0.85rem; margin-right: 0.5rem;">
                                Score: {score:.2f} / 10
                            </span>
                            <span style="background-color: {color}22; color: {color}; font-weight: 800; padding: 0.3rem 0.75rem; border-radius: 6px; font-size: 0.85rem; border: 1px solid {color};">
                                {status}
                            </span>
                        </div>
                    </div>
                    <p style="color: #334155; font-size: 0.95rem; margin-bottom: 0.8rem; line-height: 1.5;">
                        <strong>Problem Statement:</strong> {row['problem_statement']}
                    </p>
                    <div style="background-color: #F8FAFC; border-left: 3px solid #00D09C; padding: 0.6rem 0.9rem; border-radius: 4px; margin-bottom: 0.8rem;">
                        <span style="font-size: 0.88rem; color: #1E293B;"><strong>Proposed Intervention:</strong> {row['proposed_intervention']}</span>
                    </div>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.82rem; color: #64748B;">
                        <span>Stage: <strong>{row['lifecycle_stage']}</strong></span>
                        <span>Prevalence: <strong>{row['prevalence_score']:.1f}</strong></span>
                        <span>Severity: <strong>{row['severity_score']:.1f}</strong></span>
                        <span>Actionability: <strong>{row['actionability_score']:.1f}</strong></span>
                        <span>Confidence: <strong>{row['evidence_confidence']:.2f}</strong></span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            col_btn, _ = st.columns([1, 4])
            with col_btn:
                if st.button(f"Inspect Dossier ({opp_id})", key=f"btn_dossier_{opp_id}"):
                    st.session_state.selected_opportunity_id = opp_id
                    st.session_state.current_page = "Opportunity Detail"
                    st.rerun()
