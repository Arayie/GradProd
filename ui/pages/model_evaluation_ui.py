"""
Model Evaluation and Benchmark Dashboard
Displays empirical quality metrics, F1 scores, Cohen's Kappa, and grounding rates.
"""

import streamlit as st
import json
import os
import pandas as pd

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Evaluation & Benchmarks</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Model Performance & Evaluation</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Rigorous evaluation against held-out human-annotated gold standard across English, Hindi, and Hinglish.
            </p>
        </div>
    """, unsafe_allow_html=True)

    metrics_file = "outputs/model_evaluation_metrics.json"
    if not os.path.exists(metrics_file):
        st.warning("No evaluation metrics file found. Please run scripts/run_phase_4_enrichment.py to generate benchmarks.")
        return

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f1 = metrics.get("pain_point_evaluation", {}).get("macro_f1", 0.0)
        st.metric("Pain Point Macro F1", f"{f1:.3f}", delta="Target >= 0.80")
    with col2:
        kappa = metrics.get("pain_point_evaluation", {}).get("cohens_kappa", 0.0)
        st.metric("Cohen's Kappa (κ)", f"{kappa:.3f}", delta="Target >= 0.70")
    with col3:
        life_f1 = metrics.get("lifecycle_evaluation", {}).get("macro_f1", 0.0)
        st.metric("Lifecycle Macro F1", f"{life_f1:.3f}")
    with col4:
        grounding = metrics.get("evidence_grounding_rate", 0.0) * 100
        st.metric("Direct Grounding Rate", f"{grounding:.1f}%", delta="100% Target")

    st.markdown("---")

    # Language Breakdown
    st.subheader("Multilingual Performance Breakdown")
    lang_data = metrics.get("language_breakdown", {})
    if lang_data:
        lang_rows = []
        for l_code, l_metrics in lang_data.items():
            lang_rows.append({
                "Language Cohort": "Hindi / Hinglish" if l_code == "hindi_hinglish" else "English (en)",
                "Sample Size": l_metrics.get("sample_size"),
                "Macro F1": f"{l_metrics.get('macro_f1'):.3f}",
                "Precision": f"{l_metrics.get('macro_precision'):.3f}",
                "Recall": f"{l_metrics.get('macro_recall'):.3f}",
                "Cohen's Kappa": f"{l_metrics.get('cohens_kappa'):.3f}",
            })
        st.table(pd.DataFrame(lang_rows))

    st.markdown("---")

    # Application Breakdown
    st.subheader("Application Cohort Evaluation")
    app_data = metrics.get("app_breakdown", {})
    if app_data:
        app_rows = []
        for a_name, a_metrics in app_data.items():
            app_rows.append({
                "Application": a_name,
                "Gold-Set Sample": a_metrics.get("sample_size"),
                "Macro F1": f"{a_metrics.get('macro_f1'):.3f}",
                "Accuracy": f"{a_metrics.get('accuracy'):.3f}",
            })
        st.dataframe(pd.DataFrame(app_rows), use_container_width=True)

    st.markdown("---")

    # Error Inspection
    st.subheader("Known Model Discrepancies & Audit Log")
    errors = metrics.get("classification_errors", [])
    if errors:
        st.dataframe(pd.DataFrame(errors), use_container_width=True)
    else:
        st.success("No critical classification discrepancies detected on the gold standard benchmark.")
