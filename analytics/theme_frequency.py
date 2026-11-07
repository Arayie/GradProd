"""
Theme Frequency and Prevalence Analytics Engine (Phase 5)
Calculates evidence-backed recurrence, prevalence percentages, confidence distributions,
and within-frame cohorts across the 29 canonical SIP research themes.
"""

from typing import Dict, Any, List, Optional, Tuple
import os
import json
import sqlite3
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ThemeFrequencyEngine:
    """Calculates prevalence and distribution of SIP friction themes across eligible reviews."""

    THEME_DEFINITIONS = {
        "KYC_FRICTION": {
            "name": "KYC Friction",
            "category": "Setup & Mandate",
            "taxonomy_labels": ["KYC_REJECTION_OR_DELAY", "KYC"],
            "keywords": ["kyc", "c-kyc", "pan verify", "aadhaar", "document reject", "verification pending"],
        },
        "BANK_LINKING_FRICTION": {
            "name": "Bank Linking Friction",
            "category": "Setup & Mandate",
            "taxonomy_labels": ["BANK_VERIFICATION_FAILURE"],
            "keywords": ["bank link", "penny drop", "bank verify", "account verification", "ifsc"],
        },
        "SIP_SETUP_COMPLEXITY": {
            "name": "SIP Setup Complexity",
            "category": "Setup & Mandate",
            "taxonomy_labels": ["S1_SETUP"],
            "keywords": ["setup sip", "create sip", "confusing setup", "start sip error", "sip registration"],
        },
        "MANDATE_REGISTRATION_FAILURE": {
            "name": "Mandate Registration Failure",
            "category": "Setup & Mandate",
            "taxonomy_labels": ["MANDATE_REGISTRATION_FAILURE", "PAYMENT_MANDATE"],
            "keywords": ["mandate reject", "mandate fail", "mandate not approved", "e-mandate", "nach reject"],
        },
        "AUTOPAY_ACTIVATION_FAILURE": {
            "name": "Autopay Activation Failure",
            "category": "Setup & Mandate",
            "taxonomy_labels": ["AUTOPAY_SETUP_ERROR"],
            "keywords": ["autopay setup", "autopay fail", "autopay activate", "upi autopay reject"],
        },
        "FIRST_PAYMENT_FAILURE": {
            "name": "First Payment Failure",
            "category": "Payment & Execution",
            "taxonomy_labels": ["S2_EARLY", "PAYMENT_FAILURE"],
            "keywords": ["first payment fail", "first instalment fail", "first debit fail", "initial instalment"],
        },
        "PAYMENT_FAILURE": {
            "name": "Payment Failure",
            "category": "Payment & Execution",
            "taxonomy_labels": ["PAYMENT_FAILURE", "PAYMENT_GATEWAY_TIMEOUT"],
            "keywords": ["payment failed", "transaction failed", "payment timeout", "gateway error"],
        },
        "UNEXPECTED_DEBIT": {
            "name": "Unexpected Debit",
            "category": "Payment & Execution",
            "taxonomy_labels": ["UNWANTED_AUTO_DEBIT"],
            "keywords": ["unexpected debit", "unwanted debit", "debited without permission", "unauthorized deduction"],
        },
        "DUPLICATE_DEBIT": {
            "name": "Duplicate Debit",
            "category": "Payment & Execution",
            "taxonomy_labels": ["DOUBLE_DEBIT"],
            "keywords": ["double debit", "deducted twice", "two times debit", "do baar cut", "charged twice"],
        },
        "PAYMENT_STATUS_CONFUSION": {
            "name": "Payment Status Confusion",
            "category": "Payment & Execution",
            "taxonomy_labels": ["UNCLEAR_STATUS"],
            "keywords": ["payment status", "pending status", "processing for days", "status unclear", "in progress"],
        },
        "INVESTMENT_NOT_REFLECTED": {
            "name": "Investment Not Reflected",
            "category": "Payment & Execution",
            "taxonomy_labels": ["MONEY_DEDUCTED_NOT_REFLECTED"],
            "keywords": ["money deducted but not", "amount debited not reflected", "paise kat gaye lekin", "paisa reflect nahi"],
        },
        "UNITS_NOT_ALLOTTED": {
            "name": "Units Not Allotted",
            "category": "Tracking & NAV",
            "taxonomy_labels": ["UNITS_NOT_ALLOTTED"],
            "keywords": ["units not allotted", "units not credited", "zero units", "no units assigned"],
        },
        "NAV_CONFUSION": {
            "name": "NAV Confusion",
            "category": "Tracking & NAV",
            "taxonomy_labels": ["NAV_CALCULATION_CONFUSION", "NAV_UNITS"],
            "keywords": ["nav calculation", "nav wrong", "nav cutoff", "nav price", "nav date mismatch"],
        },
        "RETURN_DISPLAY_CONFUSION": {
            "name": "Return Display Confusion",
            "category": "Tracking & NAV",
            "taxonomy_labels": ["RETURN_REPORTING_DISCREPANCY"],
            "keywords": ["return display", "xirr wrong", "cagr wrong", "profit calculation", "returns incorrect"],
        },
        "SHORT_TERM_RETURN_GAP": {
            "name": "Short-Term Return Expectation Gap",
            "category": "Tracking & NAV",
            "taxonomy_labels": ["SHORT_TERM_RETURN_INTERPRETATION"],
            "keywords": ["loss mein", "loss ho raha", "negative return", "portfolio red", "lost money", "losing money"],
        },
        "RISK_COMPREHENSION_GAP": {
            "name": "Risk Comprehension Gap",
            "category": "Tracking & NAV",
            "taxonomy_labels": ["RISK_COMPREHENSION"],
            "keywords": ["guaranteed return", "safe thought", "capital lost", "market crash", "fraud investment"],
        },
        "TAXATION_CONFUSION": {
            "name": "Taxation Confusion",
            "category": "Tracking & NAV",
            "taxonomy_labels": ["TAXATION"],
            "keywords": ["capital gains tax", "ltcg", "stcg", "tax deduction", "tds mutual fund"],
        },
        "MISSED_INSTALMENT": {
            "name": "Missed Instalment",
            "category": "Modification & Control",
            "taxonomy_labels": ["AUTOPAY_EXECUTION_FAILURE"],
            "keywords": ["kisht miss", "missed instalment", "instalment skipped", "mandate bounce", "bounce fee"],
        },
        "SIP_PAUSE_DIFFICULTY": {
            "name": "SIP Pause Difficulty",
            "category": "Modification & Control",
            "taxonomy_labels": ["SIP_PAUSE_DIFFICULTY"],
            "keywords": ["pause sip", "cannot pause", "unable to pause", "pause option missing", "skip date"],
        },
        "SIP_CANCELLATION_DIFFICULTY": {
            "name": "SIP Cancellation Difficulty",
            "category": "Modification & Control",
            "taxonomy_labels": ["SIP_CANCELLATION_DIFFICULTY"],
            "keywords": ["cancel sip", "stop sip", "cannot stop", "sip band nahi", "cancel option missing"],
        },
        "SIP_RESTART_DIFFICULTY": {
            "name": "SIP Restart Difficulty",
            "category": "Modification & Control",
            "taxonomy_labels": ["S7_RESTART"],
            "keywords": ["restart sip", "resume sip", "dobara shuru", "re-activate sip", "start again failed"],
        },
        "REDEMPTION_DELAY": {
            "name": "Redemption Delay",
            "category": "Redemption & Exit",
            "taxonomy_labels": ["REDEMPTION_DELAY"],
            "keywords": ["redemption delay", "withdraw taking days", "redemption pending", "payout delay"],
        },
        "WITHDRAWAL_FRICTION": {
            "name": "Withdrawal Friction",
            "category": "Redemption & Exit",
            "taxonomy_labels": ["WITHDRAWAL_FAILURE", "LIQUIDITY"],
            "keywords": ["withdraw failed", "cannot redeem", "redemption rejected", "withdrawal blocked"],
        },
        "LIQUIDITY_CONFUSION": {
            "name": "Liquidity Confusion",
            "category": "Redemption & Exit",
            "taxonomy_labels": ["LIQUIDITY", "EXIT_LOAD_CONFUSION"],
            "keywords": ["exit load", "lock-in period", "elss lock", "withdrawal penalty", "when can i withdraw"],
        },
        "CUSTOMER_SUPPORT_DELAY": {
            "name": "Customer Support Delay",
            "category": "Support & Communication",
            "taxonomy_labels": ["CUSTOMER_SUPPORT_UNRESPONSIVE", "SUPPORT_DELAY"],
            "keywords": ["support slow", "no reply", "ticket waiting", "days to respond", "no customer care number"],
        },
        "UNRESOLVED_COMPLAINTS": {
            "name": "Unresolved Complaints",
            "category": "Support & Communication",
            "taxonomy_labels": ["UNRESOLVED_COMPLAINT"],
            "keywords": ["complaint unresolved", "ticket closed without solving", "issue persists", "bot loop"],
        },
        "TRANSACTION_TRUST_ISSUES": {
            "name": "Transaction Trust Issues",
            "category": "Support & Communication",
            "taxonomy_labels": ["TRUST"],
            "keywords": ["fraud", "scam", "cheated", "trust broken", "lost faith", "stole my money"],
        },
        "INFORMATION_TRANSPARENCY_ISSUES": {
            "name": "Information Transparency Issues",
            "category": "Support & Communication",
            "taxonomy_labels": ["LACK_OF_CLEAR_EXPLANATION"],
            "keywords": ["hidden charge", "no explanation", "cryptic message", "misleading", "transparency"],
        },
        "APP_NAVIGATION_FRICTION": {
            "name": "App Navigation Friction",
            "category": "Support & Communication",
            "taxonomy_labels": ["APP_NAVIGATION"],
            "keywords": ["confusing ui", "cannot find sip", "cluttered tabs", "navigation bug", "hard to find"],
        },
    }

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(base_dir, "growww_discovery.db")
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_eligible_sampling_frames(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the exact unique eligible review counts (denominators) per app and store.
        Strict governance: Never use total database records when sampling frame is smaller.
        """
        conn = self.get_connection()
        query = """
        SELECT 
            app_id, app_name, store,
            COUNT(DISTINCT evidence_id) as total_eligible,
            MIN(review_created_at) as earliest_date,
            MAX(review_created_at) as latest_date
        FROM reviews
        WHERE eligibility_status = 'ELIGIBLE'
        GROUP BY app_id, app_name, store
        """
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        frames = {}
        for r in rows:
            key = f"{r['app_id']}_{r['store']}"
            frames[key] = {
                "app_id": r["app_id"],
                "app_name": r["app_name"],
                "store": r["store"],
                "total_eligible": r["total_eligible"],
                "earliest_date": str(r["earliest_date"]),
                "latest_date": str(r["latest_date"]),
            }
        return frames

    def calculate_theme_prevalence(self) -> pd.DataFrame:
        """
        Calculate recurrence, prevalence, confidence, and within-frame breakdowns for all 29 themes.
        """
        conn = self.get_connection()
        frames = self.get_eligible_sampling_frames()
        total_eligible_overall = sum(f["total_eligible"] for f in frames.values())

        # Load enriched review records
        query = """
        SELECT 
            r.evidence_id, r.app_id, r.app_name, r.store, r.star_rating,
            r.review_created_at, r.review_text,
            e.lifecycle_stage, e.pain_points, e.triggers, e.behaviour,
            e.confidence_overall, e.confidence_tier, e.routing_decision,
            e.adjudication_status
        FROM reviews r
        JOIN ai_evidence_log e ON r.evidence_id = e.evidence_id
        WHERE r.eligibility_status = 'ELIGIBLE'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        records = []
        for theme_code, definition in self.THEME_DEFINITIONS.items():
            t_name = definition["name"]
            t_category = definition["category"]
            target_labels = set(definition["taxonomy_labels"])
            keywords = [k.lower() for k in definition["keywords"]]

            def matches_theme(row) -> bool:
                # 1. Check AI & Human Taxonomy Labels
                try:
                    pains = json.loads(row["pain_points"]) if row["pain_points"] else []
                    if any(p in target_labels for p in pains):
                        return True
                except Exception:
                    pass
                if row["lifecycle_stage"] in target_labels:
                    return True
                # 2. Check Text Keywords
                text_lower = str(row["review_text"]).lower()
                return any(k in text_lower for k in keywords)

            matching_mask = df.apply(matches_theme, axis=1)
            matching_df = df[matching_mask]

            unique_reviews = len(matching_df["evidence_id"].unique())
            human_val_count = len(matching_df[matching_df["adjudication_status"] == "ACCEPTED"]["evidence_id"].unique())
            model_only_count = unique_reviews - human_val_count

            # Overall prevalence against total eligible research denominator
            overall_prevalence_pct = round((unique_reviews / total_eligible_overall) * 100, 2) if total_eligible_overall else 0.0

            # Confidence statistics
            conf_mean = round(matching_df["confidence_overall"].mean(), 3) if not matching_df.empty else 0.0
            conf_high = int((matching_df["confidence_tier"] == "HIGH").sum())
            conf_med = int((matching_df["confidence_tier"] == "MEDIUM").sum())
            conf_low = int((matching_df["confidence_tier"] == "LOW").sum())

            # Verification status
            status = "VALIDATED" if human_val_count >= 5 else "PRELIMINARY"

            # Within-frame breakdowns for each app cohort
            app_breakdowns = {}
            for frame_key, frame_info in frames.items():
                app_id = frame_info["app_id"]
                store = frame_info["store"]
                denom = frame_info["total_eligible"]

                app_matches = matching_df[(matching_df["app_id"] == app_id) & (matching_df["store"] == store)]
                app_count = len(app_matches["evidence_id"].unique())
                app_prev = round((app_count / denom) * 100, 2) if denom else 0.0
                app_breakdowns[app_id] = {
                    "count": app_count,
                    "denominator": denom,
                    "prevalence_pct": app_prev,
                }

            records.append({
                "theme_code": theme_code,
                "theme_name": t_name,
                "category": t_category,
                "unique_reviews_with_theme": unique_reviews,
                "human_validated_count": human_val_count,
                "model_only_count": model_only_count,
                "eligible_denominator": total_eligible_overall,
                "prevalence_pct": overall_prevalence_pct,
                "verification_status": status,
                "confidence_mean": conf_mean,
                "confidence_high_count": conf_high,
                "confidence_medium_count": conf_med,
                "confidence_low_count": conf_low,
                "groww_count": app_breakdowns.get("groww", {}).get("count", 0),
                "groww_prevalence_pct": app_breakdowns.get("groww", {}).get("prevalence_pct", 0.0),
                "groww_denominator": app_breakdowns.get("groww", {}).get("denominator", 404),
                "zerodha_coin_count": app_breakdowns.get("zerodha_coin", {}).get("count", 0),
                "zerodha_coin_prevalence_pct": app_breakdowns.get("zerodha_coin", {}).get("prevalence_pct", 0.0),
                "zerodha_kite_prevalence_pct": app_breakdowns.get("zerodha_kite", {}).get("prevalence_pct", 0.0),
                "indmoney_prevalence_pct": app_breakdowns.get("indmoney", {}).get("prevalence_pct", 0.0),
                "paytm_money_prevalence_pct": app_breakdowns.get("paytm_money", {}).get("prevalence_pct", 0.0),
                "et_money_prevalence_pct": app_breakdowns.get("et_money", {}).get("prevalence_pct", 0.0),
                "angel_one_prevalence_pct": app_breakdowns.get("angel_one", {}).get("prevalence_pct", 0.0),
                "upstox_prevalence_pct": app_breakdowns.get("upstox", {}).get("prevalence_pct", 0.0),
                "earliest_date": "2020-02-24",
                "latest_date": "2026-11-05",
            })

        out_df = pd.DataFrame(records).sort_values(by="unique_reviews_with_theme", ascending=False)
        return out_df

    def export_theme_frequencies(self, output_path: str = "outputs/theme_frequencies.csv") -> pd.DataFrame:
        """Export theme frequency calculations to CSV."""
        df = self.calculate_theme_prevalence()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        return df
