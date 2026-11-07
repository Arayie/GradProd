"""
Ranked Product Opportunities & Prioritization Matrix (Phase 5)
Interactive opportunity ranking, multi-factor scoring breakdown, and product intervention concepts.
"""

import streamlit as st
import pandas as pd
import os
from analytics.opportunity_scoring import OpportunityScoringEngine

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Opportunity Scoring</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Ranked Product Opportunities</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Evidence-backed product intervention opportunities ranked by Prevalence, Severity, Lifecycle Criticality, and Actionability.
            </p>
        </div>
    """, unsafe_allow_html=True)

    csv_path = "outputs/ranked_product_opportunities.csv"
    if not os.path.exists(csv_path):
        engine = OpportunityScoringEngine()
        df = engine.export_opportunities(csv_path)
    else:
        df = pd.read_csv(csv_path)

    # Opportunity Score Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Scored Opportunities", len(df))
    with col2:
        top_opp = df.iloc[0]
        st.metric("#1 Priority Opportunity", top_opp["opportunity_id"], f"Score: {top_opp['opportunity_score']:.2f}")
    with col3:
        st.metric("Top Lifecycle Target", top_opp["lifecycle_stage"])
    with col4:
        st.metric("Scoring Weights", "P:30% S:30% L:25% A:15%")

    st.markdown("---")

    # Opportunity Leaderboard Table
    st.subheader("Opportunity Prioritization Leaderboard")
    leaderboard_cols = [
        "priority_rank", "opportunity_id", "opportunity_title", "opportunity_score",
        "lifecycle_stage", "target_application", "prevalence_score", "severity_score",
        "lifecycle_criticality", "actionability_score", "evidence_confidence"
    ]
    st.dataframe(df[leaderboard_cols], use_container_width=True)

    st.markdown("---")

    # Detailed Opportunity Intervention Breakdown
    st.subheader("Detailed Opportunity Specifications & Product Concepts")

    for _, row in df.iterrows():
        score = row["opportunity_score"]
        badge_color = "#10B981" if score >= 6.0 else ("#F59E0B" if score >= 5.0 else "#64748B")

        with st.container():
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <h3 style="margin: 0; color: #0F172A; font-size: 1.15rem; font-weight: 700;">
                            #{row['priority_rank']} [{row['opportunity_id']}] {row['opportunity_title']}
                        </h3>
                        <span style="background-color: {badge_color}22; color: {badge_color}; padding: 0.25rem 0.75rem; border-radius: 12px; font-weight: 800; font-size: 0.95rem;">
                            Score: {score:.2f} / 10.0
                        </span>
                    </div>
                    <p style="color: #475569; font-size: 0.95rem; margin-bottom: 0.75rem;">
                        <strong>Target Stage:</strong> <code>{row['lifecycle_stage']}</code> • <strong>Target:</strong> {row['target_application']}
                    </p>
                    <p style="color: #334155; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0.75rem;">
                        <strong>Problem Statement:</strong> {row['problem_statement']}
                    </p>
                </div>
            """, unsafe_allow_html=True)

            with st.expander(f"View Proposed Product Interventions & Evidence ({row['opportunity_id']})"):
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**Proposed Product Interventions:**")
                    st.write(row["proposed_intervention"])
                    st.markdown("**Testable Hypothesis for 12M First-SIP Active Rate:**")
                    st.info(row["testable_hypothesis"])
                with col_right:
                    st.markdown("**Exemplar Verbatim Customer Quote:**")
                    st.warning(f"💬 *\"{row['exemplar_verbatim_quote']}\"*")
                    st.markdown("**Score Factor Breakdown:**")
                    st.write(f"- Prevalence: `{row['prevalence_score']:.2f}` (Weight: 30%)")
                    st.write(f"- Severity: `{row['severity_score']:.2f}` (Weight: 30%)")
                    st.write(f"- Lifecycle Criticality: `{row['lifecycle_criticality']:.2f}` (Weight: 25%)")
                    st.write(f"- Product Actionability: `{row['actionability_score']:.2f}` (Weight: 15%)")
                    st.write(f"- Evidence Confidence Multiplier: `{row['evidence_confidence']:.3f}`")
