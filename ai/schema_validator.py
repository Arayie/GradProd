"""
Schema Validator for AI Classification and Enrichment Output
Enforces taxonomy constraints, JSON structure, and confidence boundaries.
"""

from typing import Dict, Any, List, Tuple, Set
import json
import logging

logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validates model classification output against Phase 4 schema and taxonomy rules."""

    ALLOWED_RELEVANCE = {
        "DIRECT_SIP_RELEVANT",
        "INDIRECT_SIP_RELEVANT",
        "GENERAL_INVESTMENT_RELEVANT",
        "GENERAL_APP_FEEDBACK",
        "IRRELEVANT",
    }

    ALLOWED_LIFECYCLES = {
        "S0_DISCOVERY",
        "S1_SETUP",
        "S2_EARLY",
        "S2_FIRST_PAYMENT",
        "S3_HABIT",
        "S3_HABITUAL",
        "S4_REVIEW",
        "S4_EXPANSION",
        "S5_FRICTION",
        "S5_PAUSE",
        "S6_PAUSE_STOP",
        "S6_STOP",
        "S7_RESTART",
        "GENERAL_INVESTMENT",
        "UNKNOWN",
    }

    LIFECYCLE_CANONICAL_MAP = {
        "S2_FIRST_PAYMENT": "S2_EARLY",
        "S3_HABITUAL": "S3_HABIT",
        "S4_EXPANSION": "S4_REVIEW",
        "S5_PAUSE": "S5_FRICTION",
        "S6_STOP": "S6_PAUSE_STOP",
    }

    ALLOWED_INTENTS = {
        "DISCIPLINED_SAVING",
        "START_DISCIPLINED_SAVING",
        "LONG_TERM_WEALTH_CREATION",
        "BUILD_LONG_TERM_GOAL",
        "FIRST_TIME_INVESTING",
        "LEARNING_INVESTMENT",
        "LEARN_INVESTING",
        "TAX_PLANNING",
        "CONVENIENCE",
        "FAMILY_INFLUENCE",
        "PEER_INFLUENCE",
        "FAMILY_PEER_INFLUENCE",
        "CREATOR_ADVISER_INFLUENCE",
        "HIGH_RETURNS_EXPECTATION",
        "EMERGENCY_FUND",
        "LIQUIDITY_NEED",
        "OTHER_INTENT",
        "UNKNOWN",
    }

    ALLOWED_EXPECTATIONS = {
        "EFFORTLESS_AUTOMATION",
        "HIGH_GROWTH",
        "CAPITAL_GROWTH",
        "CAPITAL_SAFETY",
        "SAFETY_CAPITAL_PROTECTION",
        "TIMELY_SUPPORT",
        "INSTANT_WITHDRAWAL",
        "CLEAR_NAV_REPORTING",
        "PREDICTABLE_DEDUCTIONS",
        "PREDICTABLE_OUTCOME",
        "LOW_CHARGES",
        "SEAMLESS_KYC",
        "EASY_INVESTMENT",
        "ACCESS_TO_MONEY",
        "TAX_BENEFIT",
        "HABIT_FORMATION",
        "OTHER_EXPECTATION",
        "NOT_STATED",
        "UNKNOWN",
    }

    ALLOWED_BEHAVIOURS = {
        "STARTED_SIP",
        "SET_UP_MANDATE",
        "ATTEMPTED_MANDATE_SETUP",
        "CHECKED_PAYMENT_STATUS",
        "TRACKED_RETURNS",
        "MONITORED_NAV",
        "CHECK_NAV_VALUE",
        "CHECK_RETURNS",
        "CHECK_TRANSACTION_STATUS",
        "CHECK_STATEMENT",
        "MODIFIED_SIP_AMOUNT",
        "CHANGE_SIP_AMOUNT",
        "SKIPPED_INSTALMENT",
        "MISS_INSTALMENT",
        "PAUSED_SIP",
        "PAUSE_SIP",
        "ATTEMPTED_SIP_PAUSE",
        "CANCELLED_SIP",
        "ATTEMPTED_SIP_CANCELLATION",
        "REDEEMED_FUNDS",
        "REDEEM",
        "SWITCHED_APPLICATION",
        "CONTACTED_SUPPORT",
        "CONTACT_SUPPORT",
        "SEEK_EXTERNAL_EXPLANATION",
        "UNINSTALLED_APP",
        "OTHER_BEHAVIOUR",
        "NOT_STATED",
    }

    ALLOWED_PAIN_POINTS = {
        # Setup & Mandate
        "MANDATE_REGISTRATION_FAILURE",
        "AUTOPAY_SETUP_ERROR",
        "BANK_VERIFICATION_FAILURE",
        "KYC_REJECTION_OR_DELAY",
        "MANDATE_APPROVAL_DELAY",
        "PAYMENT_MANDATE",
        "KYC",
        # Payment & Execution
        "DOUBLE_DEBIT",
        "MONEY_DEDUCTED_NOT_REFLECTED",
        "AUTOPAY_EXECUTION_FAILURE",
        "PAYMENT_GATEWAY_TIMEOUT",
        "LATE_INVESTMENT_EXECUTION",
        # Tracking & NAV
        "NAV_ALLOCATION_DELAY",
        "NAV_CALCULATION_CONFUSION",
        "RETURN_REPORTING_DISCREPANCY",
        "PORTFOLIO_UPDATE_DELAY",
        "UNITS_NOT_ALLOTTED",
        "NAV_UNITS",
        "SHORT_TERM_RETURN_INTERPRETATION",
        "RISK_COMPREHENSION",
        # Modification & Control
        "SIP_PAUSE_DIFFICULTY",
        "SIP_CANCELLATION_DIFFICULTY",
        "DATE_MODIFICATION_FAILURE",
        "STEP_UP_ERROR",
        "UNWANTED_AUTO_DEBIT",
        "UNCLEAR_STATUS",
        "APP_NAVIGATION",
        # Redemption & Exit
        "REDEMPTION_DELAY",
        "WITHDRAWAL_FAILURE",
        "BANK_ACCOUNT_MISMATCH",
        "EXIT_LOAD_CONFUSION",
        "LIQUIDITY",
        "TAXATION",
        # Support & Trust
        "CUSTOMER_SUPPORT_UNRESPONSIVE",
        "GENERIC_BOT_RESPONSES",
        "UNRESOLVED_COMPLAINT",
        "LACK_OF_CLEAR_EXPLANATION",
        "SUPPORT_DELAY",
        "TRUST",
        # No Pain Point
        "NO_PAIN_POINT_STATED",
    }

    ALLOWED_TRIGGERS = {
        "PAYMENT_FAILURE",
        "MANDATE_FAILURE",
        "MISSED_MANDATE",
        "MARKET_CORRECTION",
        "MARKET_MOVEMENT",
        "NEGATIVE_RETURN_PERCEPTION",
        "LOW_PERCEIVED_PROGRESS",
        "UNEXPECTED_CHARGE",
        "UNHELPFUL_SUPPORT_RESPONSE",
        "APP_UPDATE_GLITCH",
        "APP_INCIDENT",
        "PERSONAL_CASH_CRUNCH",
        "INCOME_CHANGE",
        "UNEXPECTED_EXPENSE",
        "TAX_EVENT",
        "FAMILY_ADVICE",
        "LIFE_GOAL_CHANGE",
        "OTHER_TRIGGER",
        "NOT_STATED",
    }

    ALLOWED_OUTSIDE_APP = {
        "CONTACTED_BANK",
        "CONTACTED_AMC",
        "CONTACTED_CUSTOMER_SUPPORT",
        "CUSTOMER_SUPPORT",
        "CHECKED_BANK_STATEMENT",
        "WATCHED_YOUTUBE_OR_TUTORIAL",
        "ONLINE_VIDEO",
        "ASKED_FRIEND_OR_FAMILY",
        "FRIENDS_FAMILY",
        "COMPLAINED_ON_SOCIAL_MEDIA",
        "SWITCHED_TO_ANOTHER_APP",
        "SEARCH_ENGINE",
        "FINANCIAL_ADVISER",
        "FINANCIAL_NEWS",
        "UNINSTALLED_APP",
        "OTHER_WORKAROUND",
        "OTHER",
        "NOT_STATED",
    }

    ALLOWED_OUTCOMES = {
        "CONTINUED_SIP",
        "CONTINUED",
        "PAUSED_SIP",
        "PAUSED",
        "STOPPED_SIP",
        "STOPPED",
        "SWITCHED_PLATFORM",
        "LOST_MONEY_PERCEPTION",
        "RESOLVED_AFTER_DELAY",
        "REDUCED",
        "RESTARTED",
        "REDEEMED",
        "UNRESOLVED",
        "SATISFIED",
        "CHURNED",
        "NOT_STATED",
    }

    REQUIRED_KEYS = [
        "evidence_id",
        "primary_research_relevance",
        "lifecycle_stage",
        "secondary_lifecycle_stages",
        "investor_intent",
        "expectations",
        "behaviour",
        "pain_points",
        "triggers",
        "outside_app_actions",
        "reported_outcome",
        "confidence_scores",
        "evidence_spans",
    ]

    def validate(self, data: Any) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate a dictionary against the Phase 4 schema.
        Returns (is_valid, errors, validated_data).
        """
        errors = []
        if not isinstance(data, dict):
            return False, ["Output must be a JSON object"], {}

        validated = dict(data)

        # Check required keys
        for key in self.REQUIRED_KEYS:
            if key not in validated:
                errors.append(f"Missing required key: {key}")

        # Validate & normalize relevance
        rel = validated.get("primary_research_relevance", "IRRELEVANT")
        if rel not in self.ALLOWED_RELEVANCE:
            errors.append(f"Invalid primary_research_relevance: {rel}")
            validated["primary_research_relevance"] = "IRRELEVANT"

        # Validate & normalize lifecycle stage
        stage = validated.get("lifecycle_stage", "UNKNOWN")
        if stage in self.LIFECYCLE_CANONICAL_MAP:
            stage = self.LIFECYCLE_CANONICAL_MAP[stage]
            validated["lifecycle_stage"] = stage
        if stage not in self.ALLOWED_LIFECYCLES:
            errors.append(f"Invalid lifecycle_stage: {stage}")
            validated["lifecycle_stage"] = "UNKNOWN"

        # Secondary stages
        sec_stages = validated.get("secondary_lifecycle_stages", [])
        if not isinstance(sec_stages, list):
            validated["secondary_lifecycle_stages"] = []
        else:
            norm_sec = []
            for s in sec_stages:
                norm_s = self.LIFECYCLE_CANONICAL_MAP.get(s, s)
                if norm_s in self.ALLOWED_LIFECYCLES:
                    norm_sec.append(norm_s)
            validated["secondary_lifecycle_stages"] = norm_sec

        # Validate lists: investor_intent, expectations, behaviour, pain_points, triggers, outside_app_actions
        for field, allowed_set, default_val in [
            ("investor_intent", self.ALLOWED_INTENTS, "UNKNOWN"),
            ("expectations", self.ALLOWED_EXPECTATIONS, "NOT_STATED"),
            ("behaviour", self.ALLOWED_BEHAVIOURS, "NOT_STATED"),
            ("pain_points", self.ALLOWED_PAIN_POINTS, "NO_PAIN_POINT_STATED"),
            ("triggers", self.ALLOWED_TRIGGERS, "NOT_STATED"),
            ("outside_app_actions", self.ALLOWED_OUTSIDE_APP, "NOT_STATED"),
        ]:
            val_list = validated.get(field, [])
            if not isinstance(val_list, list):
                val_list = [val_list] if val_list else [default_val]
            
            clean_list = []
            for item in val_list:
                item_str = str(item).strip()
                if item_str in allowed_set:
                    clean_list.append(item_str)
                else:
                    errors.append(f"Unknown {field} label: '{item_str}'")
            if not clean_list:
                clean_list = [default_val]
            validated[field] = clean_list

        # Validate reported_outcome
        outcome = validated.get("reported_outcome", "NOT_STATED")
        if outcome not in self.ALLOWED_OUTCOMES:
            errors.append(f"Invalid reported_outcome: {outcome}")
            validated["reported_outcome"] = "NOT_STATED"

        # Validate confidence scores
        conf = validated.get("confidence_scores", {})
        if not isinstance(conf, dict):
            conf = {}
        clean_conf = {}
        for sub_k in ["overall", "lifecycle_stage", "investor_intent", "pain_points", "reported_outcome"]:
            val = conf.get(sub_k, 0.70)
            try:
                val = float(val)
                val = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                val = 0.50
                errors.append(f"Invalid confidence score for {sub_k}")
            clean_conf[sub_k] = round(val, 3)
        validated["confidence_scores"] = clean_conf

        # Validate evidence_spans
        spans = validated.get("evidence_spans", {})
        if not isinstance(spans, dict):
            spans = {}
        validated["evidence_spans"] = spans

        # Validate disclosed_context (strict privacy default UNKNOWN)
        context = validated.get("disclosed_context", {})
        if not isinstance(context, dict):
            context = {}
        validated["disclosed_context"] = {
            "age_band": str(context.get("age_band", "UNKNOWN")),
            "investment_experience": str(context.get("investment_experience", "UNKNOWN")),
            "income_stability": str(context.get("income_stability", "UNKNOWN")),
        }

        # Reason summary
        validated["reasoning_summary"] = str(validated.get("reasoning_summary", "")).strip()

        is_valid = len(errors) == 0
        return is_valid, errors, validated
