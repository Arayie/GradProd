"""
SIP Lifecycle & Friction Transition Analytics Engine (Phase 5)
Analyzes stage-by-stage progression, drop-off triggers, and friction hot spots across S0-S7.
"""

from typing import Dict, Any, List, Optional
import os
import json
import sqlite3
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class LifecycleAnalyticsEngine:
    """Analyzes customer journey progression, friction clustering, and drop-off risks across 8 SIP stages."""

    LIFECYCLE_ORDER = [
        "S0_DISCOVERY",
        "S1_SETUP",
        "S2_EARLY",
        "S3_HABIT",
        "S4_REVIEW",
        "S5_FRICTION",
        "S6_PAUSE_STOP",
        "S7_RESTART",
        "GENERAL_INVESTMENT",
    ]

    LIFECYCLE_NAMES = {
        "S0_DISCOVERY": "S0 Discovery & Onboarding",
        "S1_SETUP": "S1 Mandate & Autopay Setup",
        "S2_EARLY": "S2 First Payment & Allotment",
        "S3_HABIT": "S3 Habitual Recurring Debits",
        "S4_REVIEW": "S4 Expansion & Step-Up SIP",
        "S5_FRICTION": "S5 Friction & Date Modification",
        "S6_PAUSE_STOP": "S6 Cancellation & Redemption",
        "S7_RESTART": "S7 Resumption & Restart",
        "GENERAL_INVESTMENT": "General Mutual Fund Feedback",
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

    def analyze_lifecycle_stages(self) -> pd.DataFrame:
        """Analyze stage distribution, ratings, dominant pain points, and churn risk."""
        conn = self.get_connection()
        query = """
        SELECT 
            e.lifecycle_stage, e.app_name, e.pain_points, e.behaviour,
            e.triggers, e.reported_outcome, e.confidence_overall,
            r.star_rating, r.evidence_id, r.review_text
        FROM ai_evidence_log e
        JOIN reviews r ON e.evidence_id = r.evidence_id
        WHERE r.eligibility_status = 'ELIGIBLE'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        total_reviews = len(df)
        records = []

        for stage_code in self.LIFECYCLE_ORDER:
            stage_name = self.LIFECYCLE_NAMES.get(stage_code, stage_code)
            stage_df = df[df["lifecycle_stage"] == stage_code]
            count = len(stage_df)
            share_pct = round((count / total_reviews) * 100, 2) if total_reviews else 0.0

            if count > 0:
                avg_rating = round(stage_df["star_rating"].mean(), 2)
                pct_negative = round(((stage_df["star_rating"] <= 2).sum() / count) * 100, 1)

                # Extract dominant pain points
                pains = []
                for p in stage_df["pain_points"].dropna():
                    try:
                        pains.extend(json.loads(p))
                    except Exception:
                        pass
                pain_series = pd.Series([p for p in pains if p != "NO_PAIN_POINT_STATED"])
                top_pain = pain_series.value_counts().index[0] if not pain_series.empty else "NO_PAIN_POINT_STATED"
                top_pain_count = int(pain_series.value_counts().iloc[0]) if not pain_series.empty else 0

                # Churn / Drop-off indicator count
                stop_outcomes = stage_df["reported_outcome"].isin(["STOPPED_SIP", "PAUSED_SIP", "CHURNED"]).sum()
                drop_off_risk_pct = round((stop_outcomes / count) * 100, 1)
            else:
                avg_rating = 0.0
                pct_negative = 0.0
                top_pain = "NONE"
                top_pain_count = 0
                drop_off_risk_pct = 0.0

            # Criticality weighting for opportunity scoring (1 to 10)
            criticality_map = {
                "S1_SETUP": 10.0,
                "S2_EARLY": 9.5,
                "S5_FRICTION": 8.5,
                "S6_PAUSE_STOP": 8.0,
                "S3_HABIT": 6.5,
                "S0_DISCOVERY": 5.0,
                "S4_REVIEW": 5.0,
                "S7_RESTART": 7.0,
                "GENERAL_INVESTMENT": 4.0,
            }

            records.append({
                "stage_code": stage_code,
                "stage_name": stage_name,
                "review_count": count,
                "share_pct": share_pct,
                "average_star_rating": avg_rating,
                "negative_rating_pct": pct_negative,
                "dominant_pain_point": top_pain,
                "dominant_pain_count": top_pain_count,
                "drop_off_risk_pct": drop_off_risk_pct,
                "stage_criticality_weight": criticality_map.get(stage_code, 5.0),
            })

        return pd.DataFrame(records)

    def export_lifecycle_analytics(self, output_path: str = "outputs/lifecycle_journey_analytics.csv") -> pd.DataFrame:
        """Export lifecycle stage analytics to CSV."""
        df = self.analyze_lifecycle_stages()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        return df
