"""
Data Integrity and Metric Segregation Tests for Growww Discovery Engine.
Verifies:
1. Synthetic records are strictly excluded from genuine review metrics.
2. Unverified records (PENDING) are not counted as eligible research evidence.
3. Genuine permitted reviews (ELIGIBLE) are accurately counted.
4. Empty database produces zero review metrics (no None/null values).
5. Loading demo data does not alter production review counts.
6. Restarting the application / reconnecting to SQLite preserves the correct counts.
"""
import unittest
import os
import sys
import tempfile
import sqlite3

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import DatabaseConnection
from database.repositories import ReviewRepository
from core.database_manager import DatabaseManager
from core.sample_data import SampleDataManager
from core.config_loader import get_config_loader

class TestDataIntegrityAndMetrics(unittest.TestCase):
    """Test suite ensuring absolute separation between synthetic demo records and genuine evidence."""

    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = DatabaseConnection(self.temp_db_path)
        self.config_loader = get_config_loader()
        
        self.db_mgr = DatabaseManager(self.db, self.config_loader)
        self.db_mgr.initialize()

        self.review_repo = ReviewRepository(self.db)
        self.sample_mgr = SampleDataManager(self.review_repo)

    def tearDown(self):
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def _insert_mock_review(self, evidence_id: str, app_id: str, store: str, eligibility: str, rating: int = 5):
        """Helper to insert mock review with specific eligibility status."""
        self.review_repo.insert_review({
            "evidence_id": evidence_id,
            "app_id": app_id,
            "store": store,
            "source_record_id": f"rec_{evidence_id}",
            "review_title": f"Review {evidence_id}",
            "review_text": f"Review content text for {evidence_id} with SIP details.",
            "star_rating": rating,
            "review_created_at": "2026-11-01 10:00:00",
            "collection_method": "test_collector",
            "eligibility_status": eligibility,
            "redaction_status": "CLEAN"
        })

    def test_01_empty_database_produces_zero_metrics(self):
        """Criterion 4: Empty database produces exact zeroes across all review metrics."""
        metrics = self.review_repo.get_summary_metrics()
        self.assertEqual(metrics["total_records"], 0)
        self.assertEqual(metrics["genuine_reviews"], 0)
        self.assertEqual(metrics["total_reviews"], 0)
        self.assertEqual(metrics["eligible_reviews"], 0)
        self.assertEqual(metrics["pending_reviews"], 0)
        self.assertEqual(metrics["rejected_reviews"], 0)
        self.assertEqual(metrics["demo_reviews"], 0)
        self.assertEqual(metrics["store_distribution"], {})
        self.assertEqual(metrics["rating_distribution"], {})

    def test_02_synthetic_records_excluded_from_genuine_review_metrics(self):
        """Criterion 1: Synthetic records are excluded from genuine reviews and eligible evidence."""
        # Insert 3 synthetic demo reviews
        self._insert_mock_review("DEMO_001", "groww", "google_play", "SYNTHETIC_DEMO")
        self._insert_mock_review("DEMO_002", "groww", "google_play", "SYNTHETIC_DEMO")
        self._insert_mock_review("DEMO_003", "groww", "apple_app_store", "SYNTHETIC_DEMO")

        metrics = self.review_repo.get_summary_metrics()

        # Total records stored reflects the 3 records
        self.assertEqual(metrics["total_records"], 3)
        self.assertEqual(metrics["demo_reviews"], 3)

        # Genuine reviews and eligible research records MUST remain exactly 0
        self.assertEqual(metrics["genuine_reviews"], 0, "Synthetic records must NOT be counted as genuine reviews")
        self.assertEqual(metrics["total_reviews"], 0, "total_reviews alias must NOT count synthetic records")
        self.assertEqual(metrics["eligible_reviews"], 0, "Synthetic records must NOT count toward eligible research")

        # Distribution charts must remain empty
        self.assertEqual(metrics["store_distribution"], {}, "Charts must exclude synthetic records")
        self.assertEqual(metrics["rating_distribution"], {}, "Rating chart must exclude synthetic records")

    def test_03_unverified_records_are_not_eligible(self):
        """Criterion 2: Unverified records (PENDING) are counted as genuine but NOT eligible."""
        self._insert_mock_review("PEND_001", "groww", "google_play", "PENDING")
        self._insert_mock_review("PEND_002", "groww", "google_play", "PENDING")

        metrics = self.review_repo.get_summary_metrics()

        self.assertEqual(metrics["total_records"], 2)
        self.assertEqual(metrics["genuine_reviews"], 2)
        self.assertEqual(metrics["pending_reviews"], 2)
        self.assertEqual(metrics["eligible_reviews"], 0, "PENDING reviews must not be eligible")
        self.assertEqual(metrics["demo_reviews"], 0)

    def test_04_genuine_permitted_reviews_counted_correctly(self):
        """Criterion 3: Permitted genuine reviews (ELIGIBLE) are accurately counted."""
        # Insert 2 genuine ELIGIBLE reviews and 1 REJECTED review
        self._insert_mock_review("ELIG_001", "groww", "apple_app_store", "ELIGIBLE", rating=5)
        self._insert_mock_review("ELIG_002", "groww", "google_play", "ELIGIBLE", rating=4)
        self._insert_mock_review("REJ_001", "groww", "google_play", "REJECTED", rating=1)
        # Plus 1 demo review
        self._insert_mock_review("DEMO_001", "groww", "google_play", "SYNTHETIC_DEMO", rating=2)

        metrics = self.review_repo.get_summary_metrics()

        self.assertEqual(metrics["total_records"], 4)
        self.assertEqual(metrics["genuine_reviews"], 3) # 2 eligible + 1 rejected
        self.assertEqual(metrics["eligible_reviews"], 2)
        self.assertEqual(metrics["rejected_reviews"], 1)
        self.assertEqual(metrics["demo_reviews"], 1)

        # Store distribution must reflect only the 3 genuine reviews
        self.assertEqual(metrics["store_distribution"].get("apple_app_store"), 1)
        self.assertEqual(metrics["store_distribution"].get("google_play"), 2)

    def test_05_loading_demo_data_does_not_alter_production_review_counts(self):
        """Criterion 5: Loading demo data does not alter production review counts."""
        # Insert 2 genuine production reviews
        self._insert_mock_review("PROD_001", "groww", "apple_app_store", "ELIGIBLE")
        self._insert_mock_review("PROD_002", "groww", "google_play", "ELIGIBLE")

        metrics_before = self.review_repo.get_summary_metrics()
        self.assertEqual(metrics_before["genuine_reviews"], 2)
        self.assertEqual(metrics_before["eligible_reviews"], 2)
        self.assertEqual(metrics_before["demo_reviews"], 0)

        # Now load 30+ synthetic demo records
        loaded = self.sample_mgr.load_demo_records()
        self.assertGreaterEqual(loaded, 30)

        metrics_after = self.review_repo.get_summary_metrics()

        # Production metrics must remain unchanged
        self.assertEqual(metrics_after["genuine_reviews"], 2, "Loading demo data altered genuine_reviews!")
        self.assertEqual(metrics_after["eligible_reviews"], 2, "Loading demo data altered eligible_reviews!")
        self.assertEqual(metrics_after["demo_reviews"], loaded)
        self.assertEqual(metrics_after["total_records"], 2 + loaded)

    def test_06_restarting_application_preserves_correct_counts(self):
        """Criterion 6: Reconnecting to SQLite preserves exact counts."""
        self._insert_mock_review("PERSIST_001", "groww", "apple_app_store", "ELIGIBLE")
        self._insert_mock_review("PERSIST_002", "groww", "google_play", "SYNTHETIC_DEMO")

        # Simulate application restart with a new connection instance to same database file
        new_db_conn = DatabaseConnection(self.temp_db_path)
        new_repo = ReviewRepository(new_db_conn)

        metrics = new_repo.get_summary_metrics()
        self.assertEqual(metrics["total_records"], 2)
        self.assertEqual(metrics["genuine_reviews"], 1)
        self.assertEqual(metrics["eligible_reviews"], 1)
        self.assertEqual(metrics["demo_reviews"], 1)

if __name__ == "__main__":
    unittest.main()
