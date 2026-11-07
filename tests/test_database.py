"""
Unit Tests for Database Foundation, Schema, Repositories, and Persistence.
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
from database.repositories import AppRepository, ReviewRepository, compute_content_hash
from core.exceptions import DuplicateRecordError, DatabaseError

class TestDatabaseFoundation(unittest.TestCase):
    """Test suite validating SQLite schema, constraints, and persistence."""

    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = DatabaseConnection(self.temp_file.name)
        self.db.initialize_schema()
        self.app_repo = AppRepository(self.db)
        self.review_repo = ReviewRepository(self.db)

        # Seed sample app
        self.app_repo.sync_from_config([{
            "internal_id": "test_groww",
            "official_name": "Groww Test App",
            "developer_name": "Groww Devs",
            "role": "primary_case_study",
            "apple_app_store": {"app_id": "111", "verification_status": "VERIFIED"},
            "google_play_store": {"package_name": "com.test.groww", "verification_status": "VERIFIED"}
        }])

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except Exception:
                pass

    def test_01_schema_tables_exist(self):
        """Verify that all 6 required tables are created."""
        expected_tables = {"apps", "source_routes", "reviews", "ingestion_runs", "collection_errors", "import_batches"}
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertTrue(expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}")

    def test_02_review_insertion_and_persistence(self):
        """Verify inserting a review and reading it back across new connection."""
        review_text = "Simple and great SIP experience for beginners."
        c_hash = compute_content_hash(review_text)
        review_data = {
            "evidence_id": "EV_TEST_001",
            "app_id": "test_groww",
            "store": "google_play",
            "source_record_id": "rec_001",
            "review_title": "Great App",
            "review_text": review_text,
            "star_rating": 5,
            "review_created_at": "2026-10-01 10:00:00",
            "content_hash": c_hash,
            "eligibility_status": "ELIGIBLE"
        }
        row_id = self.review_repo.insert_review(review_data)
        self.assertGreater(row_id, 0)

        # Reopen connection and verify persistence
        new_db = DatabaseConnection(self.temp_file.name)
        new_repo = ReviewRepository(new_db)
        records, total = new_repo.query_reviews(app_id="test_groww")
        self.assertEqual(total, 1)
        self.assertEqual(records[0]["review_text"], review_text)
        self.assertEqual(records[0]["star_rating"], 5)

    def test_03_duplicate_records_rejected(self):
        """Verify that inserting duplicate reviews with same source_record_id raises DuplicateRecordError."""
        review_text = "Good mutual fund platform."
        review_data = {
            "evidence_id": "EV_TEST_DUP_1",
            "app_id": "test_groww",
            "store": "google_play",
            "source_record_id": "same_id_100",
            "review_text": review_text,
            "star_rating": 4,
            "review_created_at": "2026-10-02 12:00:00"
        }
        self.review_repo.insert_review(review_data)

        # Attempt duplicate insertion
        duplicate_data = review_data.copy()
        duplicate_data["evidence_id"] = "EV_TEST_DUP_2"
        with self.assertRaises(DuplicateRecordError):
            self.review_repo.insert_review(duplicate_data)

    def test_04_invalid_rating_constraint(self):
        """Verify that SQLite CHECK constraint rejects ratings outside 1-5."""
        review_data = {
            "evidence_id": "EV_TEST_BAD_RATING",
            "app_id": "test_groww",
            "store": "google_play",
            "source_record_id": "bad_rating_rec",
            "review_text": "Rating test",
            "star_rating": 6,  # Invalid
            "review_created_at": "2026-10-02 12:00:00"
        }
        with self.assertRaises(DatabaseError):
            self.review_repo.insert_review(review_data)

    def test_05_foreign_key_enforcement(self):
        """Verify foreign key constraint on app_id (cannot insert review for non-existent app)."""
        review_data = {
            "evidence_id": "EV_TEST_NON_EXISTENT_APP",
            "app_id": "non_existent_app_id",
            "store": "google_play",
            "review_text": "Foreign key test",
            "star_rating": 4,
            "review_created_at": "2026-10-02 12:00:00"
        }
        with self.assertRaises(DatabaseError):
            self.review_repo.insert_review(review_data)

if __name__ == "__main__":
    unittest.main()
