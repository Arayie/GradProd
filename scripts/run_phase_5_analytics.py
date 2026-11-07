#!/usr/bin/env python3
"""
Phase 5 Analytics & Opportunity Scoring Batch Execution Script
Calculates theme prevalence, lifecycle friction, cross-app benchmarks,
multi-factor opportunity scores, and retention continuation scenarios.
"""

import os
import sys
import logging

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

LIB_DIR = os.path.join(REPO_ROOT, "lib")
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from services.analytics_service import AnalyticsService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("=================================================================")
    logger.info("   GROWWW INVESTOR DISCOVERY ENGINE: PHASE 5 ANALYTICS PIPELINE  ")
    logger.info("=================================================================")

    service = AnalyticsService()
    results = service.run_full_analytics_pipeline(outputs_dir="outputs")

    logger.info("=================================================================")
    logger.info("                 PHASE 5 ANALYTICS EXECUTION SUMMARY             ")
    logger.info("=================================================================")
    logger.info(f"Total SIP Research Themes Quantified: {results['total_themes_analyzed']}")
    logger.info(f"Top Identified Theme:                 {results['top_theme']} ({results['top_theme_prevalence']}%)")
    logger.info(f"Applications Benchmarked:             {results['apps_benchmarked']}")
    logger.info(f"Prioritized Product Opportunities:    {results['opportunities_ranked']}")
    logger.info(f"#1 Ranked Opportunity:                {results['top_opportunity']} (Score: {results['top_opportunity_score']:.2f})")
    logger.info(f"Retention Scenarios Modeled:          {results['retention_scenarios_modeled']}")
    logger.info("Exported Datasets:")
    for key, path in results["exported_files"].items():
        logger.info(f"  - {key}: {path}")
    logger.info("=================================================================")

if __name__ == "__main__":
    main()
