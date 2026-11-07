"""
12-Month First-SIP Retention & Continuation Simulator (Phase 5)
Interactive sensitivity modeling of product interventions on first-year SIP continuation.
Strict Governance: Qualitative discovery hypothesis modeling; not internal transaction telemetry.
"""

import streamlit as st
import pandas as pd
import os
from analytics.retention_modeling import RetentionHypothesisEngine

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Retention Modeling</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">12-Month First-SIP Continuation Modeling</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Modeling the theoretical impact of friction-removal product interventions on the 12-Month First-SIP Active Rate.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Governance Notice
    st.markdown("""
        <div class="demo-banner">
            <strong>RESEARCH GOVERNANCE DISCLAIMER:</strong> This simulator operates strictly as an independent qualitative 
            discovery hypothesis model based on customer friction observed in public reviews. It does <strong>NOT</strong> 
            represent internal Groww customer database cohorts, audited financial ledgers, or definitive proof of cohort retention.
        </div>
    """, unsafe_allow_html=True)

    csv_path = "outputs/sip_retention_hypotheses.csv"
    if not os.path.exists(csv_path):
        engine = RetentionHypothesisEngine()
        df = engine.export_retention_hypotheses(csv_path)
    else:
        df = pd.read_csv(csv_path)

    # Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Baseline Active Rate (Est.)", "32.0%", "Status Quo")
    with col2:
        st.metric("Top Single Intervention Uplift", "+29.7%", "S1 Mandate Fallback")
    with col3:
        st.metric("Holistic Overhaul Potential", "53.6%", "+67.5% Relative Uplift")
    with col4:
        st.metric("Primary Drop-off Stage", "S1 Setup & Mandate", "Highest Leverage")

    st.markdown("---")

    # Modeled Scenarios Comparison
    st.subheader("Modeled Product Intervention Scenarios")
    
    chart_df = df.set_index("scenario_name")[["estimated_12m_active_rate_pct"]]
    st.bar_chart(chart_df)

    st.markdown("---")

    # Scenarios Table
    table_cols = [
        "scenario_name", "targeted_stage", "modeled_s1_mandate_drop_pct",
        "modeled_s2_early_panic_drop_pct", "modeled_s5_friction_churn_pct",
        "estimated_12m_active_rate_pct", "continuation_uplift_pct", "priority"
    ]
    renamed = {
        "scenario_name": "Intervention Scenario",
        "targeted_stage": "Target Stage",
        "modeled_s1_mandate_drop_pct": "S1 Mandate Drop %",
        "modeled_s2_early_panic_drop_pct": "S2 Early Panic Drop %",
        "modeled_s5_friction_churn_pct": "S5 Friction Churn %",
        "estimated_12m_active_rate_pct": "Est. 12M Active Rate %",
        "continuation_uplift_pct": "Uplift %",
        "priority": "Priority",
    }
    st.dataframe(df[table_cols].rename(columns=renamed), use_container_width=True)

    st.markdown("---")

    # Interactive Custom Sensitivity Simulator
    st.subheader("Interactive Friction-Reduction Sensitivity Simulator")
    st.write("Adjust friction reduction percentages to simulate custom product impact on the 12-month first-SIP journey:")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        s1_reduction = st.slider("S1 Mandate Setup Drop Reduction", min_value=0, max_value=80, value=50, step=5, format="%d%%")
    with col_s2:
        s2_reduction = st.slider("S2 T+2 Unit Allotment Panic Reduction", min_value=0, max_value=80, value=55, step=5, format="%d%%")
    with col_s3:
        s5_reduction = st.slider("S5 Missed Instalment Churn Reduction", min_value=0, max_value=80, value=50, step=5, format="%d%%")

    # Custom calculation
    base_s1 = 28.0 * (1 - s1_reduction / 100.0)
    base_s2 = 18.0 * (1 - s2_reduction / 100.0)
    base_s5 = 22.0 * (1 - s5_reduction / 100.0)

    # Simplified continuation funnel: 100 -> S1 pass -> S2 pass -> S5 survive 12m
    funnel_s1 = 100.0 * (1 - base_s1 / 100.0)
    funnel_s2 = funnel_s1 * (1 - base_s2 / 100.0)
    simulated_12m_rate = round(funnel_s2 * (1 - base_s5 / 100.0), 1)
    simulated_uplift = round(((simulated_12m_rate - 32.0) / 32.0) * 100.0, 1)

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric("Simulated 12-Month First-SIP Active Rate", f"{simulated_12m_rate:.1f}%")
    with col_res2:
        st.metric("Simulated Relative Continuation Uplift", f"{simulated_uplift:+.1f}%", delta=f"{simulated_uplift:+.1f}% vs Baseline")

    st.info("""
        **Key Analytical Takeaway:**
        Removing friction at **Stage S1 (Mandate Setup)** provides the single highest compounding leverage on the 12-month active rate. 
        Because every dropped user at S1 never attempts S2 or S3, proactive mandate fallback and instant visual status tracking generate outsized long-term retention dividends.
    """)
