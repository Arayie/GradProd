"""
Confidence Scoring and Human Review Routing Engine
Enforces PRD confidence boundaries and safety overrides for high-severity pain points.
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

class ConfidenceRouter:
    """Routes enriched review records based on confidence scores, severity rules, and grounding status."""

    HIGH_THRESHOLD = 0.80
    MEDIUM_THRESHOLD = 0.65

    CRITICAL_MANDATORY_PAIN_POINTS = {
        "MANDATE_REGISTRATION_FAILURE",
        "AUTOPAY_SETUP_ERROR",
        "BANK_VERIFICATION_FAILURE",
        "DOUBLE_DEBIT",
        "MONEY_DEDUCTED_NOT_REFLECTED",
        "AUTOPAY_EXECUTION_FAILURE",
        "UNWANTED_AUTO_DEBIT",
        "SIP_PAUSE_DIFFICULTY",
        "SIP_CANCELLATION_DIFFICULTY",
        "REDEMPTION_DELAY",
        "WITHDRAWAL_FAILURE",
        "BANK_ACCOUNT_MISMATCH",
        "PAYMENT_MANDATE",
        "TRUST",
    }

    @classmethod
    def evaluate_routing(
        cls,
        confidence_scores: Dict[str, float],
        pain_points: List[str],
        lifecycle_stage: str,
        grounding_status: str,
    ) -> Tuple[str, str, List[str]]:
        """
        Evaluate confidence tier, routing decision, and triggered rationale.
        Returns:
            (confidence_tier, routing_decision, routing_reasons)
            where:
                confidence_tier: 'HIGH' | 'MEDIUM' | 'LOW'
                routing_decision: 'AUTO_PUBLISH' | 'SAMPLE_AUDIT' | 'MANDATORY_REVIEW'
        """
        overall_score = confidence_scores.get("overall", 0.70)
        reasons = []

        # 1. Base tier from overall confidence score
        if overall_score >= cls.HIGH_THRESHOLD:
            tier = "HIGH"
            decision = "AUTO_PUBLISH"
        elif overall_score >= cls.MEDIUM_THRESHOLD:
            tier = "MEDIUM"
            decision = "SAMPLE_AUDIT"
            reasons.append(f"Medium confidence ({overall_score:.2f}) requires sample audit")
        else:
            tier = "LOW"
            decision = "MANDATORY_REVIEW"
            reasons.append(f"Low confidence ({overall_score:.2f}) triggers mandatory review")

        # 2. Critical pain point override
        critical_detected = [p for p in pain_points if p in cls.CRITICAL_MANDATORY_PAIN_POINTS]
        if critical_detected:
            decision = "MANDATORY_REVIEW"
            reasons.append(
                f"Critical pain point detected ({', '.join(critical_detected)}): mandatory human verification required"
            )

        # 3. Stop / Pause lifecycle override
        if lifecycle_stage in ("S5_FRICTION", "S6_PAUSE_STOP", "S5_PAUSE", "S6_STOP"):
            if decision == "AUTO_PUBLISH":
                decision = "SAMPLE_AUDIT"
                reasons.append(f"Lifecycle stage {lifecycle_stage} involves friction/stop; escalated to sample audit")

        # 4. Grounding status override
        if grounding_status == "UNSUPPORTED":
            tier = "LOW"
            decision = "MANDATORY_REVIEW"
            reasons.append("Evidence spans could not be grounded in source text: mandatory review required")
        elif grounding_status == "PARTIALLY_GROUNDED" and decision == "AUTO_PUBLISH":
            decision = "SAMPLE_AUDIT"
            reasons.append("Some evidence spans are missing exact grounding: sample audit required")

        return tier, decision, reasons
