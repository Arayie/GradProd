"""
Unit and Integration Test Suite for Phase 5: Discovery Analytics, SIP Pain-Point Quantification & Opportunity Scoring
Tests theme frequency calculations, within-frame denominators, lifecycle friction, cross-app benchmarks,
multi-factor opportunity scoring, and retention hypothesis simulation.
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np

# Ensure local workspace packages in lib/ and repo root are available
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

LIB_DIR = os.path.join(REPO_ROOT, "lib")
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from analytics.theme_frequency import ThemeFrequencyEngine
from analytics.lifecycle_analytics import LifecycleAnalyticsEngine
from analytics.benchmarking import CrossAppBenchmarkEngine
from analytics.opportunity_scoring import OpportunityScoringEngine
from analytics.retention_modeling import RetentionHypothesisEngine
from services.analytics_service import AnalyticsService

class TestPhase5AnalyticsSuite(unittest.TestCase):
    """Comprehensive test suite for Phase 5 analytics, benchmarks, and scoring invariants."""

    @classmethod
    def setUpClass(cls):
        cls.theme_engine = ThemeFrequencyEngine()
        cls.lifecycle_engine = LifecycleAnalyticsEngine()
        cls.benchmark_engine = CrossAppBenchmarkEngine()
        cls.opportunity_engine = OpportunityScoringEngine()
        cls.retention_engine = RetentionHypothesisEngine()
        cls.analytics_service = AnalyticsService()

    def test_01_eligible_sampling_frame_denominators(self):
        """Verify sampling frames use actual unique eligible review denominators, not total DB rows."""
        frames = self.theme_engine.get_eligible_sampling_frames()
        self.assertEqual(len(frames), 8, "Expected exactly 8 application-store sampling frames")

        # Invariant: Each app must have its verified eligible count
        groww_frame = frames.get("groww_apple_app_store")
        self.assertIsNotNone(groww_frame)
        self.assertEqual(groww_frame["total_eligible"], 404, "Groww eligible denominator must equal 404")

        coin_frame = frames.get("zerodha_coin_apple_app_store")
        self.assertIsNotNone(coin_frame)
        self.assertEqual(coin_frame["total_eligible"], 500, "Zerodha Coin eligible denominator must equal 500")

        total_eligible = sum(f["total_eligible"] for f in frames.values())
        self.assertEqual(total_eligible, 3790, "Total eligible research reviews must equal 3,790")

    def test_02_theme_frequency_prevalence_calculation(self):
        """Verify 29 themes are quantified with valid prevalence percentages and verification statuses."""
        df_themes = self.theme_engine.calculate_theme_prevalence()
        self.assertEqual(len(df_themes), 29, "Expected exactly 29 canonical SIP themes quantified")

        # Invariants on calculated metrics
        for _, r in df_themes.iterrows():
            self.assertGreaterEqual(r["unique_reviews_with_theme"], 0)
            self.assertGreaterEqual(r["prevalence_pct"], 0.0)
            self.assertLessEqual(r["prevalence_pct"], 100.0)
            self.assertIn(r["verification_status"], ["VALIDATED", "PRELIMINARY"])
            self.assertEqual(
                r["unique_reviews_with_theme"],
                r["human_validated_count"] + r["model_only_count"],
                "Unique reviews must equal sum of human-validated and model-only reviews"
            )

        # Check top recurring theme
        top_theme = df_themes.iloc[0]
        self.assertEqual(top_theme["theme_code"], "UNRESOLVED_COMPLAINTS")
        self.assertEqual(top_theme["verification_status"], "VALIDATED")

    def test_03_lifecycle_journey_and_drop_off_analysis(self):
        """Verify lifecycle analytics tracks all 8 stages, negative ratings, and criticality weights."""
        df_life = self.lifecycle_engine.analyze_lifecycle_stages()
        self.assertEqual(len(df_life), 9, "Expected 8 SIP stages plus general investment")

        stages_found = set(df_life["stage_code"])
        expected_stages = {
            "S0_DISCOVERY", "S1_SETUP", "S2_EARLY", "S3_HABIT",
            "S4_REVIEW", "S5_FRICTION", "S6_PAUSE_STOP", "S7_RESTART",
            "GENERAL_INVESTMENT"
        }
        self.assertEqual(stages_found, expected_stages)

        # Criticality invariants: S1 Setup and S2 Early must have highest leverage weights
        s1_row = df_life[df_life["stage_code"] == "S1_SETUP"].iloc[0]
        s2_row = df_life[df_life["stage_code"] == "S2_EARLY"].iloc[0]
        self.assertGreaterEqual(s1_row["stage_criticality_weight"], 9.0)
        self.assertGreaterEqual(s2_row["stage_criticality_weight"], 9.0)

    def test_04_cross_application_benchmarking_and_rppi(self):
        """Verify cross-app benchmarks calculate Relative Pain Point Index (RPPI) across all 8 apps."""
        df_bench = self.benchmark_engine.run_benchmarks()
        self.assertEqual(len(df_bench), 8, "Expected 8 benchmarked applications")

        # Invariant: RPPI values must be non-negative
        for _, r in df_bench.iterrows():
            self.assertGreaterEqual(r["rppi_payment"], 0.0)
            self.assertIn(r["competitive_position"], ["OUTPERFORMING", "VULNERABLE"])

        # Check Groww specific positioning
        groww_row = df_bench[df_bench["app_id"] == "groww"].iloc[0]
        self.assertGreaterEqual(groww_row["average_star_rating"], 2.7)
        self.assertEqual(groww_row["competitive_position"], "OUTPERFORMING")

    def test_05_multi_factor_opportunity_scoring(self):
        """Verify opportunity scoring formula, ranking order, and required intervention fields."""
        df_opps = self.opportunity_engine.score_and_rank_opportunities()
        self.assertEqual(len(df_opps), 7, "Expected exactly 7 candidate opportunities scored")

        # Invariant: Score bounds and strictly decreasing ranks
        prev_score = 100.0
        for idx, (_, r) in enumerate(df_opps.iterrows(), 1):
            self.assertEqual(r["priority_rank"], idx)
            score = r["opportunity_score"]
            self.assertGreater(score, 0.0)
            self.assertLessEqual(score, 10.0)
            self.assertLessEqual(score, prev_score)
            prev_score = score

            # Qualitative justification invariants
            self.assertTrue(len(r["problem_statement"]) > 20)
            self.assertTrue(len(r["proposed_intervention"]) > 20)
            self.assertTrue(len(r["testable_hypothesis"]) > 20)
            self.assertTrue(len(r["exemplar_verbatim_quote"]) > 10)

    def test_06_retention_hypothesis_simulation(self):
        """Verify retention hypothesis scenarios and strict governance notice."""
        df_ret = self.retention_engine.model_retention_hypotheses()
        self.assertEqual(len(df_ret), 5, "Expected 5 modeled continuation scenarios")

        # Invariant: Baseline scenario exists with 0 uplift
        baseline = df_ret[df_ret["scenario_id"] == "SCEN-01"].iloc[0]
        self.assertEqual(baseline["continuation_uplift_pct"], 0.0)

        # Invariant: Combined overhaul produces positive uplift
        overhaul = df_ret[df_ret["scenario_id"] == "SCEN-05"].iloc[0]
        self.assertGreater(overhaul["estimated_12m_active_rate_pct"], baseline["estimated_12m_active_rate_pct"])
        self.assertGreater(overhaul["continuation_uplift_pct"], 50.0)

    def test_07_analytics_service_e2e_exports(self):
        """Verify end-to-end execution of full Phase 5 analytics pipeline and CSV file generation."""
        res = self.analytics_service.run_full_analytics_pipeline(outputs_dir="outputs")
        self.assertEqual(res["total_themes_analyzed"], 29)
        self.assertEqual(res["apps_benchmarked"], 8)
        self.assertEqual(res["opportunities_ranked"], 7)

        for _, file_path in res["exported_files"].items():
            self.assertTrue(os.path.exists(file_path), f"File {file_path} must exist")
            self.assertGreater(os.path.getsize(file_path), 100, f"File {file_path} is unexpectedly small")

if __name__ == "__main__":
    unittest.main()
