"""
Investor Behaviour Analytics Dashboard (Page 6 - Phase 6)
Dedicated behavioral research dashboard analyzing investor motivations, expectations,
triggers, coping mechanisms, and reported outcomes across SIP journeys.
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
from collections import Counter
from core.database_manager import get_database_manager

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Investor Behaviour</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Investor Behaviour & Coping Mechanisms</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Empirical synthesis of motivations, expectations, behavioral actions, triggers, and outside-app coping workarounds.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    query = """
    SELECT 
        e.evidence_id, e.app_name, e.investor_intent, e.expectations,
        e.behaviour, e.triggers, e.outside_app_actions, e.reported_outcome,
        r.star_rating, r.review_text, r.language_detected
    FROM ai_evidence_log e
    JOIN reviews r ON e.evidence_id = r.evidence_id
    WHERE r.eligibility_status = 'ELIGIBLE'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    total_records = len(df)
    st.markdown(f"**Analyzing {total_records:,} Enriched Customer Feedback Records**")

    # Helper function to unpack JSON array columns
    def unpack_counts(col_name: str) -> Counter:
        c = Counter()
        for item in df[col_name].dropna():
            try:
                arr = json.loads(item) if isinstance(item, str) else item
                if isinstance(arr, list):
                    for val in arr:
                        if val not in ("UNKNOWN", "NOT_STATED"):
                            c[val] += 1
            except Exception:
                pass
        return c

    intent_counts = unpack_counts("investor_intent")
    exp_counts = unpack_counts("expectations")
    beh_counts = unpack_counts("behaviour")
    trig_counts = unpack_counts("triggers")
    coping_counts = unpack_counts("outside_app_actions")
    outcome_counts = Counter(df["reported_outcome"].dropna())

    # Section A & B: Motivations & Expectations
    st.subheader("1. Investor Motivations & Expectations")
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("**Stated Motivations (Why Investors Start SIPs):**")
        if intent_counts:
            intent_df = pd.DataFrame([
                {"Motivation": k, "Mentions": v, "Share %": round((v / total_records) * 100, 2)}
                for k, v in intent_counts.most_common(7)
            ])
            st.dataframe(intent_df, use_container_width=True)
            st.bar_chart(intent_df.set_index("Motivation")["Mentions"])
        else:
            st.info("No explicit motivations stated.")

    with col_m2:
        st.markdown("**Investor Expectations:**")
        if exp_counts:
            exp_df = pd.DataFrame([
                {"Expectation": k, "Mentions": v, "Share %": round((v / total_records) * 100, 2)}
                for k, v in exp_counts.most_common(7)
            ])
            st.dataframe(exp_df, use_container_width=True)
            st.bar_chart(exp_df.set_index("Expectation")["Mentions"])
        else:
            st.info("No explicit expectations stated.")

    st.markdown("---")

    # Section C & D: Behaviours & Triggers
    st.subheader("2. Reported Behaviours & Friction Triggers")
    col_b1, col_b2 = st.columns(2)

    with col_b1:
        st.markdown("**Reported In-App Behaviours:**")
        if beh_counts:
            beh_df = pd.DataFrame([
                {"Behaviour": k, "Mentions": v, "Share %": round((v / total_records) * 100, 2)}
                for k, v in beh_counts.most_common(7)
            ])
            st.dataframe(beh_df, use_container_width=True)
            st.bar_chart(beh_df.set_index("Behaviour")["Mentions"])
        else:
            st.info("No distinct behaviours logged.")

    with col_b2:
        st.markdown("**Friction Triggers:**")
        if trig_counts:
            trig_df = pd.DataFrame([
                {"Trigger": k, "Mentions": v, "Share %": round((v / total_records) * 100, 2)}
                for k, v in trig_counts.most_common(7)
            ])
            st.dataframe(trig_df, use_container_width=True)
            st.bar_chart(trig_df.set_index("Trigger")["Mentions"])
        else:
            st.info("No distinct triggers logged.")

    st.markdown("---")

    # Section E & F: Coping Workarounds & Reported Outcomes
    st.subheader("3. Outside-App Coping Workarounds & Outcomes")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown("**Coping Mechanisms (When Apps Fail):**")
        if coping_counts:
            coping_df = pd.DataFrame([
                {"Workaround": k, "Mentions": v, "Share %": round((v / total_records) * 100, 2)}
                for k, v in coping_counts.most_common(7)
            ])
            st.dataframe(coping_df, use_container_width=True)
            st.bar_chart(coping_df.set_index("Workaround")["Mentions"])
        else:
            st.info("No outside-app actions reported.")

    with col_c2:
        st.markdown("**Reported Final Outcomes:**")
        clean_outcomes = {k: v for k, v in outcome_counts.items() if k != "NOT_STATED"}
        if clean_outcomes:
            out_df = pd.DataFrame([
                {"Outcome": k, "Mentions": v, "Share %": round((v / total_records) * 100, 2)}
                for k, v in clean_outcomes.items()
            ])
            st.dataframe(out_df, use_container_width=True)
            st.bar_chart(out_df.set_index("Outcome")["Mentions"])
        else:
            st.info("Outcomes predominantly unstated.")
