"""
Human Review and Adjudication Workbench
Interactive interface for expert validation, label correction, and evidence audit trails.
"""

import streamlit as st
import pandas as pd
import json
from services.human_review_service import HumanReviewService
from ai.schema_validator import SchemaValidator

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Human Review Workbench</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Human Review & Adjudication Workbench</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Audit AI predictions, adjudicate low-confidence classifications, and build gold-standard validation ground truth.
            </p>
        </div>
    """, unsafe_allow_html=True)

    reviewer = HumanReviewService()

    # Load pending adjudications
    pending_items = reviewer.get_pending_adjudications(limit=50)

    if not pending_items:
        st.success("🎉 All queued review records have been adjudicated! No pending low-confidence records.")
        return

    st.markdown(f"**{len(pending_items)} Records Awaiting Review** (Prioritizing Mandatory Reviews & Low Confidence)")

    # Select an item to inspect
    item_options = [
        f"[{i['evidence_id']}] {i['app_name']} (Conf: {i['confidence_overall']:.2f}) - {i['review_text'][:60]}..."
        for i in pending_items
    ]
    selected_idx = st.selectbox("Select Record to Adjudicate", options=range(len(pending_items)), format_func=lambda idx: item_options[idx])

    current_item = pending_items[selected_idx]
    ev_id = current_item["evidence_id"]
    enr_id = current_item["enrichment_id"]

    # Display review context
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.write(f"**App:** {current_item['app_name']}")
        st.write(f"**Rating:** {'⭐' * int(current_item['star_rating'])}")
    with col_info2:
        st.write(f"**Confidence:** {current_item['confidence_overall']:.2f} ({current_item['confidence_tier']})")
        st.write(f"**Routing:** {current_item['routing_decision']}")
    with col_info3:
        st.write(f"**Language:** {current_item['language_detected']}")
        st.write(f"**Grounding:** {current_item['evidence_grounding_status']}")

    st.markdown("### Source Review Text")
    st.info(f"\"{current_item['review_text']}\"")

    # Current AI Predictions
    st.markdown("### AI Predictions & Grounded Spans")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.write(f"**Predicted Lifecycle Stage:** `{current_item['lifecycle_stage']}`")
        ai_pains = json.loads(current_item["pain_points"]) if current_item["pain_points"] else []
        st.write(f"**Predicted Pain Points:** {ai_pains}")
    with col_p2:
        ai_intent = json.loads(current_item["investor_intent"]) if current_item["investor_intent"] else []
        st.write(f"**Predicted Intent:** {ai_intent}")
        st.write(f"**Reported Outcome:** `{current_item['reported_outcome']}`")

    spans = json.loads(current_item["evidence_spans"]) if current_item["evidence_spans"] else {}
    if spans:
        st.markdown("**Verbatim Evidence Spans:**")
        for lbl, sp in spans.items():
            if sp:
                st.code(f"{lbl}: \"{sp}\"")

    st.markdown("---")
    st.markdown("### Human Adjudication Decision")

    adjudicator_id = st.text_input("Adjudicator Identifier", value="Senior_Product_Researcher_01")
    action = st.radio("Adjudication Action", options=["ACCEPT", "CORRECT", "REJECT"], horizontal=True)

    correct_labels = []
    if action == "CORRECT":
        allowed_pains = sorted(list(SchemaValidator.ALLOWED_PAIN_POINTS))
        correct_labels = st.multiselect("Correct Pain Point Labels", options=allowed_pains, default=ai_pains)

    rationale = st.text_area(
        "Adjudication Rationale (Required)",
        placeholder="Explain why this classification was accepted, corrected, or rejected based on text evidence..."
    )

    if st.button("Submit Human Adjudication", type="primary"):
        if not rationale.strip():
            st.error("Please provide an adjudication rationale explaining the decision.")
        else:
            final_labels = ai_pains if action == "ACCEPT" else (correct_labels if action == "CORRECT" else ["REJECTED_UNSUPPORTED"])
            adj_id = reviewer.record_adjudication(
                evidence_id=ev_id,
                enrichment_id=enr_id,
                adjudicator_id=adjudicator_id,
                action=action,
                dimension="pain_points",
                original_labels=ai_pains,
                adjudicated_labels=final_labels,
                rationale=rationale,
                original_spans=spans,
                adjudicated_spans=spans if action != "REJECT" else {},
            )
            st.success(f"Adjudication #{adj_id} successfully recorded! Record status updated.")
            st.rerun()
