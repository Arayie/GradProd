"""
Cross-Application Competitive Benchmarking Engine (Phase 5)
Calculates Relative Pain Point Index (RPPI), competitive positioning, and vulnerability hotspots.
"""

from typing import Dict, Any, List, Optional
import os
import json
import sqlite3
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class CrossAppBenchmarkEngine:
    """Benchmarks Groww against peer Indian investment platforms on SIP journey friction."""

    APP_REGISTRY_NAMES = {
        "groww": "Groww",
        "zerodha_coin": "Zerodha Coin",
        "zerodha_kite": "Zerodha Kite",
        "indmoney": "INDmoney",
        "paytm_money": "Paytm Money",
        "et_money": "ET Money",
        "angel_one": "Angel One",
        "upstox": "Upstox",
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

    def run_benchmarks(self) -> pd.DataFrame:
        """Run full cross-app comparison across all 8 candidate apps."""
        conn = self.get_connection()

        # Load all eligible reviews with AI enrichment
        query = """
        SELECT 
            r.evidence_id, r.app_id, r.app_name, r.store, r.star_rating,
            r.review_created_at, r.review_text,
            e.lifecycle_stage, e.pain_points, e.reported_outcome
        FROM reviews r
        JOIN ai_evidence_log e ON r.evidence_id = e.evidence_id
        WHERE r.eligibility_status = 'ELIGIBLE'
        """
        df = pd.read_sql_query(query, conn)

        # Total eligible denominators per app
        cursor = conn.cursor()
        cursor.execute("SELECT app_id, COUNT(*) FROM reviews WHERE eligibility_status = 'ELIGIBLE' GROUP BY app_id")
        denominators = dict(cursor.fetchall())
        conn.close()

        records = []

        # Define key friction groupings
        def has_mandate_friction(row):
            text = str(row["review_text"]).lower()
            return "mandate" in text or "autopay" in text or "nach" in text

        def has_payment_friction(row):
            text = str(row["review_text"]).lower()
            return "deducted" in text or "kat gaye" in text or "double debit" in text or "reflect" in text

        def has_nav_friction(row):
            text = str(row["review_text"]).lower()
            return "nav" in text or "unit" in text or "allot" in text or "xirr" in text

        def has_support_friction(row):
            text = str(row["review_text"]).lower()
            return "support" in text or "ticket" in text or "bot" in text or "reply" in text

        def has_cancel_friction(row):
            text = str(row["review_text"]).lower()
            return "cancel" in text or "pause" in text or "stop" in text

        # Compute benchmark values across all apps
        app_metrics = {}
        for app_id, clean_name in self.APP_REGISTRY_NAMES.items():
            app_df = df[df["app_id"] == app_id]
            denom = denominators.get(app_id, len(app_df))

            m_mandate = app_df.apply(has_mandate_friction, axis=1).sum()
            m_payment = app_df.apply(has_payment_friction, axis=1).sum()
            m_nav = app_df.apply(has_nav_friction, axis=1).sum()
            m_support = app_df.apply(has_support_friction, axis=1).sum()
            m_cancel = app_df.apply(has_cancel_friction, axis=1).sum()

            avg_rating = round(app_df["star_rating"].mean(), 2) if not app_df.empty else 0.0
            pct_one_star = round(((app_df["star_rating"] == 1).sum() / denom) * 100, 1) if denom else 0.0
            pct_five_star = round(((app_df["star_rating"] == 5).sum() / denom) * 100, 1) if denom else 0.0

            app_metrics[app_id] = {
                "app_name": clean_name,
                "sampling_denominator": denom,
                "enriched_sample": len(app_df),
                "average_rating": avg_rating,
                "one_star_pct": pct_one_star,
                "five_star_pct": pct_five_star,
                "mandate_prev": round((m_mandate / denom) * 100, 2) if denom else 0.0,
                "payment_prev": round((m_payment / denom) * 100, 2) if denom else 0.0,
                "nav_prev": round((m_nav / denom) * 100, 2) if denom else 0.0,
                "support_prev": round((m_support / denom) * 100, 2) if denom else 0.0,
                "cancel_prev": round((m_cancel / denom) * 100, 2) if denom else 0.0,
            }

        # Calculate Industry Averages
        avg_mandate = np.mean([m["mandate_prev"] for m in app_metrics.values()])
        avg_payment = np.mean([m["payment_prev"] for m in app_metrics.values()])
        avg_nav = np.mean([m["nav_prev"] for m in app_metrics.values()])
        avg_support = np.mean([m["support_prev"] for m in app_metrics.values()])
        avg_cancel = np.mean([m["cancel_prev"] for m in app_metrics.values()])

        # Build final benchmark records with Relative Pain Point Index (RPPI)
        for app_id, m in app_metrics.items():
            rppi_mandate = round(m["mandate_prev"] / max(0.01, avg_mandate), 2)
            rppi_payment = round(m["payment_prev"] / max(0.01, avg_payment), 2)
            rppi_support = round(m["support_prev"] / max(0.01, avg_support), 2)

            # Groww relative positioning
            records.append({
                "app_id": app_id,
                "app_name": m["app_name"],
                "sampling_denominator": m["sampling_denominator"],
                "enriched_reviews_count": m["enriched_sample"],
                "average_star_rating": m["average_rating"],
                "one_star_pct": m["one_star_pct"],
                "five_star_pct": m["five_star_pct"],
                "mandate_friction_pct": m["mandate_prev"],
                "payment_friction_pct": m["payment_prev"],
                "nav_reporting_friction_pct": m["nav_prev"],
                "support_friction_pct": m["support_prev"],
                "cancellation_friction_pct": m["cancel_prev"],
                "rppi_mandate": rppi_mandate,
                "rppi_payment": rppi_payment,
                "rppi_support": rppi_support,
                "competitive_position": "OUTPERFORMING" if rppi_payment < 1.0 else "VULNERABLE",
            })

        out_df = pd.DataFrame(records).sort_values(by="average_star_rating", ascending=False)
        return out_df

    def export_benchmarks(self, output_path: str = "outputs/cross_app_benchmarks.csv") -> pd.DataFrame:
        """Export cross-app benchmarking table to CSV."""
        df = self.run_benchmarks()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        return df
