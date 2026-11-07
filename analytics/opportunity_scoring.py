"""
SIP Opportunity Scoring & Prioritization Engine (Phase 5)
Ranks actionable product intervention opportunities using multi-factor evidence scoring:
Prevalence (30%), Severity (30%), Lifecycle Criticality (25%), Actionability (15%) * Evidence Confidence.
"""

from typing import Dict, Any, List, Optional
import os
import json
import sqlite3
import pandas as pd
import numpy as np
import logging

from analytics.theme_frequency import ThemeFrequencyEngine

logger = logging.getLogger(__name__)

class OpportunityScoringEngine:
    """Prioritizes product opportunities based on customer friction evidence and retention criticality."""

    CANDIDATE_OPPORTUNITIES = [
        {
            "opportunity_id": "OPP-01",
            "title": "Proactive Mandate Status Tracker & Instant UPI Autopay Fallback",
            "theme_code": "MANDATE_REGISTRATION_FAILURE",
            "lifecycle_stage": "S1_SETUP",
            "problem_statement": "First-time investors encounter opaque bank mandate delays and e-mandate rejections, resulting in abandonment before the first instalment.",
            "severity_score": 9.5,
            "actionability_score": 9.0,
            "target_app": "Groww & Peers",
            "proposed_intervention": "1. Live visual mandate stepper showing bank/NPCI verification stages.\n2. Instant 1-click fallback to alternate UPI handle or netbanking if primary bank rejects.\n3. Automatic WhatsApp/SMS reminder with direct re-authorization link.",
            "testable_hypothesis": "Providing real-time mandate progress and instant alternate payment fallback will increase S1 mandate success rates by 18-25% and reduce first-instalment drop-off.",
            "exemplar_quote": "I started my first SIP but the mandate is not getting approved even after several attempts.",
        },
        {
            "opportunity_id": "OPP-02",
            "title": "Transparent T+2 NAV & Unit Allotment Lifecycle Visualizer",
            "theme_code": "INVESTMENT_NOT_REFLECTED",
            "lifecycle_stage": "S2_EARLY",
            "problem_statement": "Money is deducted from the investor's bank account, but units are not allotted until T+2, leading beginner investors to fear their funds are lost or stolen.",
            "severity_score": 9.8,
            "actionability_score": 9.5,
            "target_app": "Groww (Primary)",
            "proposed_intervention": "1. 'Money Safe & In-Transit' status card immediately upon bank debit.\n2. Visual timeline showing Debit -> AMC Order Placement -> NAV Cut-off -> Unit Allotment date.\n3. Push notification when AMC confirms unit credit with exact NAV.",
            "testable_hypothesis": "Displaying a proactive in-transit timeline immediately upon bank debit will reduce payment distress inquiries by 40% and prevent early panic uninstalls.",
            "exemplar_quote": "Paise kat gaye lekin units nahi mile abhi tak, amount deducted not reflected in portfolio.",
        },
        {
            "opportunity_id": "OPP-03",
            "title": "Frictionless 1-Click SIP Pause & Flexible Skip Mechanism",
            "theme_code": "SIP_PAUSE_DIFFICULTY",
            "lifecycle_stage": "S5_FRICTION",
            "problem_statement": "Investors facing temporary cash crunches cannot easily pause or skip an instalment, forcing them into mandate bounce penalties or full SIP cancellation.",
            "severity_score": 8.0,
            "actionability_score": 9.0,
            "target_app": "Groww & Zerodha Coin",
            "proposed_intervention": "1. 1-click 'Skip this Month' toggle directly on upcoming instalment cards.\n2. Preset pause duration (1, 2, or 3 months) with automatic continuation reminder.\n3. Zero bank bounce penalty guarantee if skipped 48h prior to debit.",
            "testable_hypothesis": "Offering a flexible, transparent pause option will prevent 30-35% of permanent SIP cancellations during short-term personal cash flow crunches.",
            "exemplar_quote": "SIP pause feature is not working in this update, unable to pause next month instalment.",
        },
        {
            "opportunity_id": "OPP-04",
            "title": "Zero-Surprise Mandate Cancellation & Debit Termination Guarantee",
            "theme_code": "SIP_CANCELLATION_DIFFICULTY",
            "lifecycle_stage": "S6_PAUSE_STOP",
            "problem_statement": "Investors who cancel an active SIP experience continued autopay deductions due to NPCI mandate de-registration latency, causing severe trust destruction.",
            "severity_score": 9.0,
            "actionability_score": 8.5,
            "target_app": "Groww & Paytm Money",
            "proposed_intervention": "1. Instant de-linking of autopay mandate with bank confirmation SMS within 2 hours.\n2. Immediate auto-refund promise if any unauthorized debit occurs post-cancellation timestamp.\n3. Transparent cancellation receipt downloadable as PDF.",
            "testable_hypothesis": "Providing an ironclad cancellation guarantee and immediate mandate revocation will protect platform trust and increase eventual S7 restart likelihood.",
            "exemplar_quote": "Even after stopping SIP money was deducted again from my bank account, worst experience.",
        },
        {
            "opportunity_id": "OPP-05",
            "title": "Automated Smart Autopay Recovery on Insufficient Balance",
            "theme_code": "MISSED_INSTALMENT",
            "lifecycle_stage": "S5_FRICTION",
            "problem_statement": "Monthly instalment fails on salary delay, triggering bank bounce charges and silent SIP stoppage without user realization.",
            "severity_score": 8.5,
            "actionability_score": 8.5,
            "target_app": "Groww & Peers",
            "proposed_intervention": "1. Balance check warning 24h prior to SIP due date.\n2. Smart retry engine attempting debit on Day +1, Day +3, and Day +5 without duplicate fees.\n3. Manual 1-click UPI instant pay option for missed monthly instalment.",
            "testable_hypothesis": "Implementing automated retry windows and manual UPI catch-up payments will recover 45% of missed monthly instalments and sustain ongoing habitual SIPs.",
            "exemplar_quote": "Kisht miss ho gayi thi because salary was 1 day late, now sip is showing stopped.",
        },
        {
            "opportunity_id": "OPP-06",
            "title": "Beginner Return Reality Context & Market Volatility Reassurance",
            "theme_code": "RETURN_DISPLAY_CONFUSION",
            "lifecycle_stage": "S3_HABIT",
            "problem_statement": "First-time investors panic when their portfolio shows short-term negative returns within months 1-3, unaware that equity mutual funds fluctuate daily.",
            "severity_score": 7.5,
            "actionability_score": 9.0,
            "target_app": "Groww & INDmoney",
            "proposed_intervention": "1. 'Why Rupee-Cost Averaging Works' visual explainer during market dips.\n2. Show number of units accumulated at discount during market correction.\n3. Option to view 3-year rolling projected range rather than daily red/green fluctuations.",
            "testable_hypothesis": "Framing market dips as 'Buying Units at a Discount' will reduce panic redemptions during the first 6 months by 20%.",
            "exemplar_quote": "Loss mein chal raha hai portfolio since 2 months, thought mutual fund gives guaranteed 15%.",
        },
        {
            "opportunity_id": "OPP-07",
            "title": "Priority Financial Transaction Support Escalation Pathway",
            "theme_code": "CUSTOMER_SUPPORT_DELAY",
            "lifecycle_stage": "S5_FRICTION",
            "problem_statement": "Investors facing critical money deductions are trapped in automated AI bot loops with no human contact, turning solvable operational bugs into 1-star rage reviews.",
            "severity_score": 9.0,
            "actionability_score": 8.0,
            "target_app": "Groww & Angel One",
            "proposed_intervention": "1. Smart triage: Any ticket containing 'money deducted' or 'mandate fail' bypasses bot directly to Tier-2 human agent.\n2. 2-hour SLA guarantee for payment discrepancies.\n3. Direct in-app callback request button for debit issues.",
            "testable_hypothesis": "Immediate human routing for money-deduction complaints will reduce 1-star review velocity by 35% and restore investor confidence.",
            "exemplar_quote": "Customer support has not responded for 5 days, bot gives same useless automated replies.",
        },
    ]

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(base_dir, "growww_discovery.db")
        self.db_path = db_path
        self.theme_engine = ThemeFrequencyEngine(db_path=db_path)

    def score_and_rank_opportunities(self) -> pd.DataFrame:
        """
        Calculates multi-factor Opportunity Scores and produces the ranked product backlog.
        Formula:
        Score = (0.30*Prevalence + 0.30*Severity + 0.25*Criticality + 0.15*Actionability) * EvidenceConfidence
        """
        # 1. Get empirical theme frequency data
        theme_df = self.theme_engine.calculate_theme_prevalence().set_index("theme_code")

        scored_records = []

        # Lifecycle stage criticality mapping
        stage_criticality = {
            "S1_SETUP": 10.0,
            "S2_EARLY": 9.5,
            "S5_FRICTION": 8.5,
            "S6_PAUSE_STOP": 8.0,
            "S3_HABIT": 6.5,
            "S4_REVIEW": 5.0,
            "S0_DISCOVERY": 5.0,
            "S7_RESTART": 7.0,
        }

        for opp in self.CANDIDATE_OPPORTUNITIES:
            t_code = opp["theme_code"]
            stage = opp["lifecycle_stage"]

            # Empirical metrics from theme frequency engine
            if t_code in theme_df.index:
                t_row = theme_df.loc[t_code]
                prev_pct = float(t_row.get("prevalence_pct", 1.0))
                human_val = int(t_row.get("human_validated_count", 0))
                conf_mean = float(t_row.get("confidence_mean", 0.85))
                unique_reviews = int(t_row.get("unique_reviews_with_theme", 10))
            else:
                prev_pct = 1.0
                human_val = 2
                conf_mean = 0.80
                unique_reviews = 5

            # 1. Prevalence Score (0 to 10 scaled logarithmically from review prevalence)
            prevalence_score = round(min(10.0, max(2.0, np.log1p(unique_reviews) * 2.2)), 2)

            # 2. Severity Score (0 to 10)
            severity_score = float(opp["severity_score"])

            # 3. Lifecycle Criticality (0 to 10)
            criticality_score = float(stage_criticality.get(stage, 6.0))

            # 4. Product Actionability (0 to 10)
            actionability_score = float(opp["actionability_score"])

            # 5. Evidence Confidence Factor (0.75 to 1.0)
            evidence_confidence = round(min(1.0, max(0.75, conf_mean * (1.0 if human_val >= 5 else 0.95))), 3)

            # Multi-factor Opportunity Score Calculation
            raw_score = (
                0.30 * prevalence_score
                + 0.30 * severity_score
                + 0.25 * criticality_score
                + 0.15 * actionability_score
            )
            final_opportunity_score = round(raw_score * evidence_confidence, 2)

            scored_records.append({
                "opportunity_id": opp["opportunity_id"],
                "opportunity_title": opp["title"],
                "theme_code": t_code,
                "lifecycle_stage": stage,
                "target_application": opp["target_app"],
                "opportunity_score": final_opportunity_score,
                "prevalence_score": prevalence_score,
                "severity_score": severity_score,
                "lifecycle_criticality": criticality_score,
                "actionability_score": actionability_score,
                "evidence_confidence": evidence_confidence,
                "empirical_review_count": unique_reviews,
                "problem_statement": opp["problem_statement"],
                "proposed_intervention": opp["proposed_intervention"],
                "testable_hypothesis": opp["testable_hypothesis"],
                "exemplar_verbatim_quote": opp["exemplar_quote"],
            })

        out_df = pd.DataFrame(scored_records).sort_values(by="opportunity_score", ascending=False)
        out_df["priority_rank"] = range(1, len(out_df) + 1)
        return out_df

    def export_opportunities(self, output_path: str = "outputs/ranked_product_opportunities.csv") -> pd.DataFrame:
        """Export ranked opportunities to CSV."""
        df = self.score_and_rank_opportunities()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        return df
