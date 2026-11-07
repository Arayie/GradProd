"""
Unit Tests for Application Registry Service.
"""
import os
import sys
import unittest

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from services.app_registry_service import get_app_registry_service

class TestAppRegistryService(unittest.TestCase):
    """Test suite validating application search, filtering, and stats."""

    def setUp(self):
        self.service = get_app_registry_service()

    def test_01_all_apps_retrieved(self):
        """Verify that all 8 candidate applications are accessible."""
        apps = self.service.get_all_apps()
        self.assertEqual(len(apps), 8)

    def test_02_search_by_keyword(self):
        """Verify searching by app name and developer name."""
        groww_res = self.service.search_apps(query="Groww")
        self.assertEqual(len(groww_res), 1)
        self.assertEqual(groww_res[0]["internal_app_id"], "groww")

        zerodha_res = self.service.search_apps(query="Zerodha")
        self.assertEqual(len(zerodha_res), 2, "Expected 2 Zerodha applications (Coin & Kite)")

    def test_03_filter_by_role(self):
        """Verify filtering by primary_case_study vs competitor roles."""
        primary_res = self.service.search_apps(role_filter="primary_case_study")
        self.assertEqual(len(primary_res), 1)
        self.assertEqual(primary_res[0]["internal_app_id"], "groww")

    def test_04_app_stats_aggregation(self):
        """Verify aggregated registry metrics."""
        stats = self.service.get_app_stats()
        self.assertEqual(stats["total_apps"], 8)
        self.assertEqual(stats["primary_apps"], 1)
        self.assertEqual(stats["competitor_apps"], 7)
        self.assertEqual(stats["apple_ready"], 8)
        self.assertEqual(stats["play_ready"], 8)

if __name__ == "__main__":
    unittest.main()
