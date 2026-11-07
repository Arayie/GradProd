"""
Unit Tests for Sample Data Mode and Demo Isolation.
"""
import os
import sys
import unittest
import tempfile

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import DatabaseConnection
from database.repositories import AppRepository, ReviewRepository
from core.sample_data import SampleDataManager
from core.config_loader import get_config_loader

class TestSampleData(unittest.TestCase):
    """Test suite validating synthetic demo data generation and strict isolation."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = DatabaseConnection(self.temp_file.name)
        self.db.initialize_schema()

        # Sync real apps from apps.yml
        config_loader = get_config_loader()
        app_repo = AppRepository(self.db)
        app_repo.sync_from_config(config_loader.get_registered_apps())

        self.review_repo = ReviewRepository(self.db)
        self.sample_mgr = SampleDataManager(self.review_repo)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except Exception:
                pass

    def test_01_load_demo_records_exceeds_thirty(self):
        """Verify that at least 30 synthetic demo records are loaded."""
        loaded = self.sample_mgr.load_demo_records()
        self.assertGreaterEqual(loaded, 30, f"Expected >= 30 demo records, loaded {loaded}")

        metrics = self.review_repo.get_summary_metrics()
        self.assertEqual(metrics["demo_reviews"], loaded)
        self.assertEqual(metrics["eligible_reviews"], 0, "Demo records must NEVER count toward eligible reviews")

    def test_02_all_records_labeled_synthetic_demo(self):
        """Verify that 100% of demo records have eligibility_status == 'SYNTHETIC_DEMO'."""
        self.sample_mgr.load_demo_records()
        reviews, total = self.review_repo.query_reviews(limit=100)
        self.assertGreater(total, 0)
        for r in reviews:
            self.assertEqual(r["eligibility_status"], "SYNTHETIC_DEMO")

    def test_03_clear_demo_records_safely_removes_them(self):
        """Verify that clearing demo records resets demo count to zero."""
        self.sample_mgr.load_demo_records()
        self.assertGreater(self.review_repo.get_summary_metrics()["demo_reviews"], 0)

        cleared = self.sample_mgr.clear_demo_records()
        self.assertGreater(cleared, 0)
        self.assertEqual(self.review_repo.get_summary_metrics()["total_reviews"], 0)

if __name__ == "__main__":
    unittest.main()
