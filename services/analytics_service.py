"""
Analytics Orchestration Service (Phase 5)
Coordinates theme frequency quantification, cross-app benchmarks, opportunity scoring,
and retention hypothesis modeling.
"""

from typing import Dict, Any, Optional
import os
import logging
import pandas as pd

from analytics.theme_frequency import ThemeFrequencyEngine
from analytics.lifecycle_analytics import LifecycleAnalyticsEngine
from analytics.benchmarking import CrossAppBenchmarkEngine
from analytics.opportunity_scoring import OpportunityScoringEngine
from analytics.retention_modeling import RetentionHypothesisEngine

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service orchestrating all analytical and opportunity scoring pipelines for Phase 5."""

    def __init__(self, db_path: Optional[str] = None):
        self.theme_engine = ThemeFrequencyEngine(db_path=db_path)
        self.lifecycle_engine = LifecycleAnalyticsEngine(db_path=db_path)
        self.benchmark_engine = CrossAppBenchmarkEngine(db_path=db_path)
        self.opportunity_engine = OpportunityScoringEngine(db_path=db_path)
        self.retention_engine = RetentionHypothesisEngine(db_path=db_path)

    def run_full_analytics_pipeline(self, outputs_dir: str = "outputs") -> Dict[str, Any]:
        """Run all analytical engines and export production CSV datasets."""
        os.makedirs(outputs_dir, exist_ok=True)
        logger.info("Executing Phase 5 Analytics Pipeline...")

        # 1. Theme Frequency & Prevalence
        p_themes = os.path.join(outputs_dir, "theme_frequencies.csv")
        df_themes = self.theme_engine.export_theme_frequencies(p_themes)
        logger.info(f"Exported {len(df_themes)} theme frequencies to {p_themes}")

        # 2. Lifecycle Journey Analytics
        p_life = os.path.join(outputs_dir, "lifecycle_journey_analytics.csv")
        df_life = self.lifecycle_engine.export_lifecycle_analytics(p_life)
        logger.info(f"Exported {len(df_life)} lifecycle stages to {p_life}")

        # 3. Cross-Application Benchmarking
        p_bench = os.path.join(outputs_dir, "cross_app_benchmarks.csv")
        df_bench = self.benchmark_engine.export_benchmarks(p_bench)
        logger.info(f"Exported {len(df_bench)} application benchmarks to {p_bench}")

        # 4. Opportunity Scoring & Ranking
        p_opps = os.path.join(outputs_dir, "ranked_product_opportunities.csv")
        df_opps = self.opportunity_engine.export_opportunities(p_opps)
        logger.info(f"Exported {len(df_opps)} ranked opportunities to {p_opps}")

        # 5. Retention Hypothesis Modeling
        p_ret = os.path.join(outputs_dir, "sip_retention_hypotheses.csv")
        df_ret = self.retention_engine.export_retention_hypotheses(p_ret)
        logger.info(f"Exported {len(df_ret)} retention scenarios to {p_ret}")

        return {
            "total_themes_analyzed": len(df_themes),
            "top_theme": df_themes.iloc[0]["theme_name"] if not df_themes.empty else "N/A",
            "top_theme_prevalence": df_themes.iloc[0]["prevalence_pct"] if not df_themes.empty else 0.0,
            "apps_benchmarked": len(df_bench),
            "opportunities_ranked": len(df_opps),
            "top_opportunity": df_opps.iloc[0]["opportunity_title"] if not df_opps.empty else "N/A",
            "top_opportunity_score": df_opps.iloc[0]["opportunity_score"] if not df_opps.empty else 0.0,
            "retention_scenarios_modeled": len(df_ret),
            "exported_files": {
                "theme_frequencies": p_themes,
                "lifecycle_analytics": p_life,
                "cross_app_benchmarks": p_bench,
                "ranked_opportunities": p_opps,
                "retention_hypotheses": p_ret,
            },
        }
