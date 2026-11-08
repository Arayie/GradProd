"""
SIP Theme Explorer (Page 7 - Phase 6)
Dedicated qualitative pain-point analytics interface with clickable theme deep-dive inspection.
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from analytics.theme_frequency import ThemeFrequencyEngine
from core.database_manager import get_database_manager
from ui.navigation import render_header

def render():
    render_header(
        "SIP Pain-Point Theme Analytics",
        "In-depth exploration of 29 canonical SIP friction themes, recurrence patterns, and grounded verbatim evidence."
    )

    csv_path = "outputs/theme_frequencies.csv"
    if not os.path.exists(csv_path):
        engine = ThemeFrequencyEngine()
        df = engine.export_theme_frequencies(csv_path)
    else:
        df = pd.read_csv(csv_path)

    # Theme selection dropdown for clickable deep-dive
    theme_options = [
        f"{r['theme_name']} ({r['category']}) - {r['unique_reviews_with_theme']} reviews ({r['prevalence_pct']}%)"
        for _, r in df.iterrows()
    ]
    selected_idx = st.selectbox("Select Theme to Inspect Deep-Dive Dossier", options=range(len(df)), format_func=lambda i: theme_options[i])
    current_theme = df.iloc[selected_idx]
    t_code = current_theme["theme_code"]

    # Top KPI Metrics for selected theme
    st.subheader(f"Theme Dossier: {current_theme['theme_name']}")
    st.caption(f"Domain: {current_theme['category']} | Verification: {current_theme['verification_status']}")

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.metric("Total Supporting Reviews", f"{current_theme['unique_reviews_with_theme']:,}")
    with t2:
        st.metric("Overall Prevalence", f"{current_theme['prevalence_pct']}%", f"Denominator: {current_theme['eligible_denominator']:,}")
    with t3:
        st.metric("Human-Validated Evidence", f"{current_theme['human_validated_count']:,}", f"Model-Only: {current_theme['model_only_count']:,}")
    with t4:
        st.metric("Mean Confidence", f"{current_theme['confidence_mean']:.2f}", f"High: {current_theme['confidence_high_count']}")

    st.markdown("---")

    # Within-Frame Cohort Prevalence Chart
    st.subheader("Cross-Application Prevalence (% of Eligible Reviews)")
    cohort_data = {
        "Groww": current_theme["groww_prevalence_pct"],
        "Zerodha Coin": current_theme["zerodha_coin_prevalence_pct"],
        "INDmoney": current_theme["indmoney_prevalence_pct"],
        "Paytm Money": current_theme["paytm_money_prevalence_pct"],
        "ET Money": current_theme["et_money_prevalence_pct"],
        "Angel One": current_theme["angel_one_prevalence_pct"],
        "Upstox": current_theme["upstox_prevalence_pct"],
        "Zerodha Kite": current_theme["zerodha_kite_prevalence_pct"],
    }
    st.bar_chart(pd.Series(cohort_data))

    st.markdown("---")

    # Verbatim Evidence Inspection from Database
    st.subheader(f"Grounded Customer Reviews Supporting '{current_theme['theme_name']}'")

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    # Query reviews matching this theme
    def_info = ThemeFrequencyEngine.THEME_DEFINITIONS.get(t_code, {})
    keywords = def_info.get("keywords", [])
    like_clauses = " OR ".join(["r.review_text LIKE ?" for _ in keywords]) if keywords else "1=1"
    like_params = [f"%{k}%" for k in keywords]

    query = f"""
    SELECT 
        r.evidence_id, r.app_name, r.star_rating, r.review_created_at,
        r.language_detected, r.review_text, e.evidence_spans,
        e.confidence_overall, e.adjudication_status
    FROM reviews r
    LEFT JOIN ai_evidence_log e ON r.evidence_id = e.evidence_id
    WHERE r.eligibility_status = 'ELIGIBLE' AND ({like_clauses})
    ORDER BY r.star_rating ASC, r.review_created_at DESC
    LIMIT 20
    """
    sample_df = pd.read_sql_query(query, conn, params=like_params)
    conn.close()

    if not sample_df.empty:
        for _, r in sample_df.head(6).iterrows():
            with st.container():
                st.markdown(f"**{r['app_name']}** • {'⭐' * int(r['star_rating'])} • {str(r['review_created_at'])[:10]} • {r['language_detected']}")
                st.write(f"\"{r['review_text']}\"")
                if r["evidence_spans"]:
                    try:
                        spans = json.loads(r["evidence_spans"])
                        for lbl, sp in spans.items():
                            if sp:
                                st.info(f"📌 Grounded Span: *\"{sp}\"* ({lbl})")
                    except Exception:
                        pass
                st.caption(f"Evidence ID: {r['evidence_id']} | Status: {r['adjudication_status']}")
                st.divider()
    else:
        st.info("No text reviews explicitly matching theme keywords.")
