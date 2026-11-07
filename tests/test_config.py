"""
Unit Tests for Application Configuration Loader.
Tests YAML validity, required fields, separation of Zerodha apps, and AppFollow removal.
"""
import os
import sys
import unittest

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from core.config_loader import ConfigLoader, get_config_loader
from core.exceptions import ConfigError

class TestConfigLoader(unittest.TestCase):
    """Test suite for ConfigLoader class."""

    def setUp(self):
        self.config_loader = get_config_loader()

    def test_01_apps_config_loads_all_eight_apps(self):
        """Verify that all 8 candidate application listings are present."""
        apps = self.config_loader.get_registered_apps()
        self.assertEqual(len(apps), 8, f"Expected 8 application listings, got {len(apps)}")
        
        internal_ids = {a["internal_id"] for a in apps}
        expected_ids = {
            "groww", "zerodha_coin", "zerodha_kite", "upstox",
            "angel_one", "indmoney", "et_money", "paytm_money"
        }
        self.assertEqual(internal_ids, expected_ids)

    def test_02_zerodha_coin_and_kite_are_separate(self):
        """Verify that Zerodha Coin and Kite have distinct app IDs and package names."""
        coin = self.config_loader.get_app_by_id("zerodha_coin")
        kite = self.config_loader.get_app_by_id("zerodha_kite")

        self.assertIsNotNone(coin)
        self.assertIsNotNone(kite)
        self.assertNotEqual(coin["apple_app_store"]["app_id"], kite["apple_app_store"]["app_id"])
        self.assertNotEqual(coin["google_play_store"]["package_name"], kite["google_play_store"]["package_name"])
        self.assertEqual(coin["google_play_store"]["package_name"], "com.zerodha.coin")
        self.assertEqual(kite["google_play_store"]["package_name"], "com.zerodha.kite3")

    def test_03_appfollow_absent_from_active_sources(self):
        """Verify that AppFollow is not active or enabled."""
        active_sources = self.config_loader.get_active_sources()
        for src in active_sources:
            self.assertNotEqual(src["source_id"], "google_play_appfollow_connector", "AppFollow must not be in active sources")

        # Verify in all sources it is marked REJECTED / disabled
        all_sources = self.config_loader.get_all_sources()
        appfollow_src = next((s for s in all_sources if s["source_id"] == "google_play_appfollow_connector"), None)
        self.assertIsNotNone(appfollow_src)
        self.assertFalse(appfollow_src.get("enabled", False))
        self.assertIn(appfollow_src.get("permission_status"), ["REJECTED", "UNAVAILABLE"])

    def test_04_taxonomy_dimensions_and_lifecycle_stages(self):
        """Verify that review taxonomy contains required dimensions and exact PRD lifecycle codes."""
        tax = self.config_loader.get_review_taxonomy_config()
        self.assertIn("dimensions", tax)
        dims = tax["dimensions"]

        expected_stages = {
            "S0_DISCOVERY", "S1_SETUP", "S2_EARLY", "S3_HABIT",
            "S4_REVIEW", "S5_FRICTION", "S6_PAUSE_STOP", "S7_RESTART"
        }
        actual_stages = set(dims["sip_lifecycle_stages"]["allowed_labels"])
        self.assertEqual(actual_stages, expected_stages)

    def test_05_missing_config_directory_raises_error(self):
        """Verify graceful error handling when config directory does not exist."""
        bad_loader = ConfigLoader(config_dir="/non/existent/path/12345")
        with self.assertRaises(ConfigError):
            bad_loader.get_apps_config()

if __name__ == "__main__":
    unittest.main()
