"""
Opportunity Detail & Product Dossier (Phase 6 - Page 10)
Comprehensive deep-dive dossier for product intervention opportunities with audited lifecycle state transitions.
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
import html
from services.opportunity_service import OpportunityService
from core.auth import AuthService, Permission

def render():
    service = OpportunityService()
    opportunities = service.get_all_opportunities()
    if not opportunities:
        st.warning("No opportunities found in discovery database.")
        return

    opp_map = {o["opportunity_id"]: o for o in opportunities}
    opp_keys = list(opp_map.keys())

    # Selected opportunity from session state or default to first
    default_id = st.session_state.get("selected_opportunity_id", opp_keys[0])
    if default_id not in opp_map:
        default_id = opp_keys[0]

    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Opportunity Dossier</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Opportunity Detail</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Evidence-grounded opportunity specification, problem breakdown, intervention design, and audited lifecycle governance.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Opportunity Selector Dropdown
    selected_id = st.selectbox(
        "Select Opportunity Dossier",
        options=opp_keys,
        format_func=lambda oid: f"#{opp_map[oid]['priority_rank']} [{oid}] {opp_map[oid]['title']} ({opp_map[oid]['lifecycle_status']})",
        index=opp_keys.index(default_id)
    )
    st.session_state.selected_opportunity_id = selected_id
    opp = opp_map[selected_id]

    status = opp["lifecycle_status"]
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

    # Header Card
    st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.8rem;">
                <div>
                    <span style="font-size: 0.85rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em;">Priority Rank #{opp['priority_rank']} • {opp['theme_code']}</span>
                    <h3 style="margin: 0.2rem 0; color: #0F172A; font-size: 1.4rem; font-weight: 800;">
                        [{opp['opportunity_id']}] {opp['title']}
                    </h3>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.7rem; font-weight: 800; color: #1E3A2F;">{opp['opportunity_score']:.2f} <span style="font-size: 0.9rem; color: #64748B;">/ 10</span></div>
                    <span style="background-color: {color}22; color: {color}; font-weight: 800; padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.85rem; border: 1px solid {color};">
                        {status}
                    </span>
                </div>
            </div>
            <div style="display: flex; gap: 2rem; font-size: 0.9rem; color: #475569; border-top: 1px solid #F1F5F9; padding-top: 0.8rem;">
                <span>Lifecycle Stage: <strong>{opp['lifecycle_stage']}</strong></span>
                <span>Target App: <strong>{opp['target_application']}</strong></span>
                <span>Primary Metric: <strong>{opp['primary_metric']}</strong></span>
                <span>Guardrail Metric: <strong>{opp['guardrail_metric']}</strong></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Tabs for Dossier Exploration
    tab_problem, tab_evidence, tab_scoring, tab_intervention, tab_governance = st.tabs([
        "1. Problem Definition",
        "2. Grounded Evidence",
        "3. Scoring Breakdown",
        "4. Product Intervention",
        "5. Lifecycle Governance & Audits"
    ])

    # 1. PROBLEM DEFINITION
    with tab_problem:
        st.markdown("### Problem Breakdown")
        st.markdown(f"""
            <div style="background-color: #F8FAFC; border-left: 4px solid #1E3A2F; padding: 1.1rem; border-radius: 4px; margin-bottom: 1.2rem;">
                <h4 style="margin-top: 0; color: #0F172A; font-size: 1.05rem;">Core Problem Statement</h4>
                <p style="color: #334155; font-size: 0.96rem; line-height: 1.5; margin: 0;">
                    {opp['problem_statement']}
                </p>
            </div>
        """, unsafe_allow_html=True)

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.markdown("#### Who is Affected?")
            st.markdown(
                "- **Primary Cohort:** First-time SIP investors and beginners entering market-linked investments.\n"
                "- **Device/Channel:** Mobile app users setting up bank auto-pay mandates and recurring debits.\n"
                "- **Sensitivity Level:** High financial anxiety; any unexpected debit or silence triggers panic."
            )
            st.markdown("#### When Does It Trigger?")
            st.markdown(
                f"- **Lifecycle Stage:** `{opp['lifecycle_stage']}`\n"
                "- **Trigger Event:** Bank mandate registration, first scheduled debit date, market fluctuation, or pause attempt."
            )

        with col_w2:
            st.markdown("#### Failure Modes & User Friction")
            st.markdown(
                "- Unclear mandate verification status leading to repeated setup attempts.\n"
                "- Silence between payment deduction and mutual fund unit allotment.\n"
                "- Lack of proactive confirmation creating immediate distrust in the platform."
            )
            st.markdown("#### Business & Retention Impact")
            st.markdown(
                "- **First-SIP Churn:** Over 35% of drop-offs occur prior to the second installment.\n"
                "- **Store Rating Degradation:** Reviewers immediately leave 1-star reviews citing 'money deducted but not invested'.\n"
                "- **Support Ticket Surge:** Customer support queues become clogged with status inquiries."
            )

    # 2. GROUNDED EVIDENCE
    with tab_evidence:
        st.markdown("### Grounded Customer Evidence")
        st.info("Directly extracted verbatim review spans supporting this opportunity from eligible customer reviews.")

        st.markdown(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.2rem;">
                <h4 style="margin-top: 0; color: #1E3A2F;">Exemplar Verbatim Evidence</h4>
                <blockquote style="font-size: 1.02rem; font-style: italic; color: #1E293B; border-left: 3px solid #00D09C; margin: 0.5rem 0; padding-left: 1rem;">
                    "{html.escape(str(opp['exemplar_verbatim_quote']))}"
                </blockquote>
                <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: #64748B; margin-top: 0.8rem;">
                    <span>Target Cohort: <strong>{opp['target_application']}</strong></span>
                    <span>Evidence Confidence: <strong>{opp['evidence_confidence'] * 100:.1f}%</strong></span>
                    <span>Prevalence Rank: <strong>High</strong></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Counter-Evidence & Mitigating Conditions")
        st.markdown(
            "> **Mitigating Finding:** For investors with existing bank netbanking familiarity or instant UPI Autopay pre-approval, "
            "setup completes without reported complaints. The friction is highly concentrated among first-time bank mandate creators "
            "and users whose banks experience multi-day batch processing delays."
        )

    # 3. SCORING BREAKDOWN
    with tab_scoring:
        st.markdown("### Multi-Factor Opportunity Scoring Breakdown")
        st.markdown("PRD Version 1.1 weighted algorithm balancing customer retention, recurrence, severity, and implementation feasibility:")

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Customer Severity (30%)", f"{opp['severity_score']:.1f} / 10", "Friction intensity")
            st.metric("Lifecycle Criticality (25%)", f"{opp['lifecycle_criticality']:.1f} / 10", "Top-of-funnel leverage")
        with sc2:
            st.metric("Prevalence Score (30%)", f"{opp['prevalence_score']:.1f} / 10", "Recurrence frequency")
            st.metric("Actionability Score (15%)", f"{opp['actionability_score']:.1f} / 10", "Feasibility / control")
        with sc3:
            st.metric("Evidence Grounding", f"{opp['evidence_confidence'] * 100:.1f}%", "Audited validation")
            st.metric("Total Weighted Score", f"{opp['opportunity_score']:.2f} / 10", "Priority Rank #" + str(opp['priority_rank']))

    # 4. PRODUCT INTERVENTION
    with tab_intervention:
        st.markdown("### Product Intervention Specification")
        st.markdown(f"""
            <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.25rem;">
                <h4 style="margin-top: 0; color: #1E3A2F;">Proposed Product Intervention</h4>
                <p style="font-size: 1.0rem; color: #1E293B; line-height: 1.5; font-weight: 500;">
                    {opp['proposed_intervention']}
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Testable Product Hypothesis")
        st.markdown(f"""
            <div style="background-color: #F0FDF4; border-left: 4px solid #16A34A; padding: 1rem; border-radius: 4px; margin-bottom: 1.25rem;">
                <p style="color: #14532D; font-size: 0.95rem; margin: 0; line-height: 1.5;">
                    <strong>Hypothesis:</strong> {opp['testable_hypothesis']}
                </p>
            </div>
        """, unsafe_allow_html=True)

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 1rem;">
                    <div style="font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase;">Primary Success Metric</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-top: 0.3rem;">{opp['primary_metric']}</div>
                    <div style="font-size: 0.85rem; color: #475569; margin-top: 0.3rem;">Targeting +15% increase in 12-month cohort retention.</div>
                </div>
            """, unsafe_allow_html=True)
        with col_m2:
            st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 1rem;">
                    <div style="font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase;">Guardrail Metric</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #DC2626; margin-top: 0.3rem;">{opp['guardrail_metric']}</div>
                    <div style="font-size: 0.85rem; color: #475569; margin-top: 0.3rem;">Ensure bounce and dispute rate stays below 0.5%.</div>
                </div>
            """, unsafe_allow_html=True)

    # 5. LIFECYCLE GOVERNANCE & AUDITS
    with tab_governance:
        st.markdown("### Lifecycle Status Governance")
        st.markdown("Manage opportunity transition states with mandatory audit trail logging.")

        can_update = AuthService.can_update_opportunities()
        current_role = AuthService.get_current_role()

        st.markdown(f"**Current User Role:** `{current_role.value}` | **Permissions:** `{'UPDATE_OPPORTUNITIES' if can_update else 'READ_ONLY'}`")

        if not can_update:
            st.warning("⚠️ **Read-Only Mode:** Your active role ('VIEWER' or 'AUDITOR') cannot modify opportunity lifecycle states. Switch to 'RESEARCHER' or 'ADMIN' in the sidebar to perform status transitions.")
        else:
            with st.form(key=f"status_update_form_{selected_id}"):
                col_st1, col_st2 = st.columns([1, 2])
                with col_st1:
                    status_options = list(OpportunityService.VALID_STATUSES)
                    new_status = st.selectbox(
                        "New Lifecycle Status",
                        options=status_options,
                        index=status_options.index(status) if status in status_options else 0
                    )
                with col_st2:
                    rationale = st.text_area(
                        "Adjudication Rationale (Mandatory)",
                        placeholder="Provide clear product research rationale for transitioning this opportunity..."
                    )

                submit_btn = st.form_submit_button("Submit Status Transition", type="primary")

                if submit_btn:
                    if not rationale.strip():
                        st.error("Adjudication rationale is required for all lifecycle state transitions.")
                    else:
                        actor = AuthService.get_current_user()
                        success = service.update_status(selected_id, new_status, actor, rationale.strip())
                        if success:
                            st.success(f"Successfully updated {selected_id} to {new_status}!")
                            st.rerun()
                        else:
                            st.error(f"Failed to update opportunity {selected_id}.")

        # Audit History Log Table
        st.markdown("---")
        st.markdown(f"#### Audit Trail History for `{selected_id}`")
        audits = service.get_opportunity_audits(selected_id)
        if audits:
            audit_df = pd.DataFrame(audits)
            st.dataframe(
                audit_df[["changed_at", "actor_id", "previous_status", "new_status", "change_rationale"]].rename(columns={
                    "changed_at": "Timestamp (UTC)",
                    "actor_id": "Actor",
                    "previous_status": "Previous Status",
                    "new_status": "New Status",
                    "change_rationale": "Rationale"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No audit transition events recorded yet for this opportunity.")
