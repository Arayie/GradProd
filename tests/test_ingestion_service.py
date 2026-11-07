"""
Integration and End-to-End Tests for Common Ingestion Service (Phase 2 MVP).
Verifies route permission gates, multi-level deduplication, canonical persistence,
PII redaction, run logging, checkpoints, and future owner stubs.
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import DatabaseConnection
from core.database_manager import DatabaseManager
from core.config_loader import get_config_loader
from services.ingestion_service import CommonIngestionService
from core.exceptions import SourcePermissionError, ValidationError, SecurityViolationError
from ingestion.deduplicate import ReviewDeduplicator, compute_canonical_content_hash
from ingestion.manual_review_csv import GooglePlayPublisherConnector, GooglePlayConsoleCSVParser

SAMPLE_APPLE_JSON = {
    "feed": {
        "entry": [
            {"im:name": {"label": "Groww"}},
            {
                "id": {"label": "20000000001"},
                "title": {"label": "SIP Debit Delay"},
                "content": {"label": "SIP amount got debited from bank but not showing on Groww app."},
                "im:rating": {"label": "2"},
                "im:version": {"label": "14.2.1"},
                "updated": {"label": "2026-11-05T12:00:00-07:00"}
            },
            {
                "id": {"label": "20000000002"},
                "title": {"label": "Smooth KYC verification"},
                "content": {"label": "Completed Aadhaar KYC in 5 minutes and started monthly SIP."},
                "im:rating": {"label": "5"},
                "im:version": {"label": "14.2.0"},
                "updated": {"label": "2026-11-04T09:30:00-07:00"}
            }
        ]
    }
}

class TestIngestionServiceIntegration(unittest.TestCase):
    """Test suite for Common Ingestion Service and data pipeline integration."""

    def setUp(self):
        # Use an isolated in-memory or temp SQLite database for test purity
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = DatabaseConnection(self.temp_db_path)
        self.config_loader = get_config_loader()
        
        # Initialize schema and sync apps & source routes
        self.db_mgr = DatabaseManager(self.db, self.config_loader)
        self.db_mgr.initialize()

        self.service = CommonIngestionService(self.db, self.config_loader)

    def tearDown(self):
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    # =========================================================================
    # 1. Permission Gate Tests
    # =========================================================================
    def test_permission_gate_blocks_rejected_appfollow(self):
        """Verifies that calling the REJECTED AppFollow connector raises SourcePermissionError."""
        with self.assertRaises(SourcePermissionError) as ctx:
            self.service._check_access_gate("google_play_appfollow_connector", admin_override=True)
        self.assertIn("REJECTED", str(ctx.exception))

    def test_permission_gate_unregistered_app_raises_validation_error(self):
        """Verifies that attempting ingestion for an unregistered app raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.service.ingest_apple_rss(app_id="non_existent_fintech_app")
        self.assertIn("Unregistered application", str(ctx.exception))

    def test_permission_gate_disabled_route_blocks_without_admin_override(self):
        """Verifies that disabled route in YAML blocks execution unless admin_override=True."""
        # Ensure route is disabled in DB
        self.db_mgr.source_repo.set_enabled("apple_app_store_public_rss", False)
        
        with self.assertRaises(SourcePermissionError) as ctx:
            self.service.ingest_apple_rss("groww", admin_override=False)
        self.assertIn("DISABLED", str(ctx.exception))

    # =========================================================================
    # 2. Deduplication Engine Tests
    # =========================================================================
    def test_deduplicator_priority_rules(self):
        """Verifies 3-tier deduplication: 1. source_record_id, 2. store+app+id, 3. content hash."""
        dedup = ReviewDeduplicator(self.db)
        
        # Initially not duplicate
        is_dup = dedup.is_duplicate(
            app_id="groww",
            store="apple_app_store",
            source_record_id="REC_99999",
            raw_text="Sample unique review content regarding SIP mandate setup."
        )
        self.assertFalse(is_dup)

        # Mark seen
        dedup.mark_seen(
            app_id="groww",
            store="apple_app_store",
            source_record_id="REC_99999",
            raw_text="Sample unique review content regarding SIP mandate setup."
        )

        # Priority 1: Exact source_record_id duplicate
        self.assertTrue(dedup.is_duplicate(
            app_id="groww",
            store="apple_app_store",
            source_record_id="REC_99999"
        ))

        # Priority 3: Identical normalized content hash even with different source ID
        self.assertTrue(dedup.is_duplicate(
            app_id="groww",
            store="apple_app_store",
            source_record_id="REC_DIFFERENT_ID_001",
            raw_text="Sample unique review content regarding SIP mandate setup."
        ))

    # =========================================================================
    # 3. Route A: Apple RSS End-to-End Pipeline
    # =========================================================================
    @patch.object(CommonIngestionService, "_check_access_gate")
    def test_apple_rss_e2e_collection_and_checkpoint(self, mock_access_gate):
        """Verifies complete Route A pipeline: fetch, deduplicate, persist, log run, checkpoint."""
        mock_access_gate.return_value = {
            "source_id": "apple_app_store_public_rss",
            "approval_reference": "PHASE2-TEST-REF-001"
        }

        with patch.object(self.service.apple_connector, "fetch_page_payload") as mock_fetch:
            mock_fetch.return_value = (200, SAMPLE_APPLE_JSON, None)

            # First run: should ingest 2 reviews
            res1 = self.service.ingest_apple_rss("groww", max_pages=1, admin_override=True)
            
            self.assertEqual(res1["status"], "COMPLETED")
            self.assertEqual(res1["accepted_count"], 2)
            self.assertEqual(res1["duplicate_count"], 0)

            # Check canonical reviews table in SQLite
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM reviews WHERE app_id = 'groww';")
                self.assertEqual(cursor.fetchone()[0], 2)

                cursor.execute("SELECT redaction_status, source_permission_id FROM reviews WHERE app_id = 'groww' LIMIT 1;")
                row = cursor.fetchone()
                self.assertEqual(row[0], "CLEAN")
                self.assertEqual(row[1], "PHASE2-TEST-REF-001")

            # Check checkpoint saved
            chk = self.db_mgr.checkpoint_repo.get_checkpoint("groww", "IN", "apple_app_store_rss")
            self.assertIsNotNone(chk)
            self.assertEqual(chk["last_seen_review_id"], "20000000001")

            # Second run: should encounter checkpoint and stop with 0 new reviews inserted
            res2 = self.service.ingest_apple_rss("groww", max_pages=1, admin_override=True)
            self.assertTrue(res2["hit_checkpoint"])
            self.assertEqual(res2["accepted_count"], 0)

    # =========================================================================
    # 4. Route B: Google Play Manual CSV Import Pipeline
    # =========================================================================
    def test_manual_csv_import_with_pii_redaction(self):
        """Verifies Route B CSV ingestion sanitizes Indian phone numbers, emails, and UPI IDs."""
        csv_content = (
            "review_text,review_date,rating,app_version\n"
            "\"Autopay failed call me at +91 9876543210 or email test@gmail.com for SIP issue\",2026-10-15,1,12.4.0\n"
            "\"Excellent portfolio tracker and mutual fund analysis tool.\",2026-10-16,5,12.4.1\n"
        )
        temp_csv = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        temp_csv.write(csv_content)
        temp_csv.close()

        try:
            res = self.service.ingest_manual_csv(
                file_or_path=temp_csv.name,
                filename="competitor_reviews.csv",
                app_id="groww",
                store="google_play",
                provenance_confirmed=True,
                permission_status="APPROVED",
                source_description="Test Competitor Reviews Dump"
            )

            self.assertEqual(res["accepted_count"], 2)
            self.assertEqual(res["total_rows"], 2)

            # Inspect database to confirm PII was redacted
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT review_text, redaction_status FROM reviews WHERE store = 'google_play';")
                rows = cursor.fetchall()
                
                # First review had PII: should contain [PHONE_REDACTED] and [EMAIL_REDACTED]
                row1_text, row1_redaction = rows[0]
                self.assertIn("[PHONE_REDACTED]", row1_text)
                self.assertIn("[EMAIL_REDACTED]", row1_text)
                self.assertNotIn("9876543210", row1_text)
                self.assertNotIn("test@gmail.com", row1_text)
                self.assertEqual(row1_redaction, "REDACTED")

                # Second review was clean
                row2_text, row2_redaction = rows[1]
                self.assertEqual(row2_redaction, "CLEAN")

        finally:
            if os.path.exists(temp_csv.name):
                os.remove(temp_csv.name)

    def test_manual_csv_requires_provenance_confirmation(self):
        """Verifies that uploading without legal provenance confirmation raises SecurityViolationError."""
        csv_content = "review_text,review_date,rating\nGreat app,2026-10-15,5\n"
        temp_csv = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        temp_csv.write(csv_content)
        temp_csv.close()

        try:
            with self.assertRaises(SecurityViolationError):
                self.service.ingest_manual_csv(
                    file_or_path=temp_csv.name,
                    filename="unconfirmed.csv",
                    app_id="groww",
                    store="google_play",
                    provenance_confirmed=False  # Violation
                )
        finally:
            if os.path.exists(temp_csv.name):
                os.remove(temp_csv.name)

    @patch.object(CommonIngestionService, "ingest_apple_rss")
    def test_ingest_all_apple_apps_orchestration(self, mock_ingest_apple):
        """Verifies batch execution across all registered Apple apps."""
        mock_ingest_apple.return_value = {
            "status": "COMPLETED",
            "pages_retrieved": 1,
            "reviews_received": 10,
            "accepted_count": 10,
            "duplicate_count": 0,
            "rejected_count": 0,
            "coverage_duration_days": 30,
            "newest_review_date": "2026-11-04T06:49:50-07:00",
            "oldest_review_date": "2026-10-04T06:49:50-07:00",
            "hit_checkpoint": False,
            "errors": []
        }

        res = self.service.ingest_all_apple_apps(max_pages=1, delay_between_apps=0.0)
        self.assertEqual(res["total_apps"], 8)
        self.assertEqual(res["total_received"], 80)
        self.assertEqual(res["total_accepted"], 80)
        self.assertEqual(mock_ingest_apple.call_count, 8)

    # =========================================================================
    # 5. Future Route C & D Extension Stubs
    # =========================================================================
    def test_route_c_google_publisher_connector_stub(self):
        """Verifies Route C connector stub is modularly defined but disabled without credentials."""
        connector = GooglePlayPublisherConnector(credentials=None)
        with self.assertRaises(SourcePermissionError) as ctx:
            connector.fetch_reviews(package_name="com.nextbillion.groww")
        self.assertIn("OWNER_AUTHENTICATION_REQUIRED", str(ctx.exception))

    def test_route_d_google_play_console_csv_parser_stub(self):
        """Verifies Route D parser stub requires authorized console provenance."""
        parser = GooglePlayConsoleCSVParser()
        with self.assertRaises(SecurityViolationError) as ctx:
            parser.parse(file_path="mock.csv", authorized_owner=False)
        self.assertIn("OWNER_AUTHORIZATION_REQUIRED", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
