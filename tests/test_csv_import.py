"""
Unit Tests for CSV Validator and Import Service.
"""
import os
import sys
import unittest
import tempfile
import pandas as pd

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from core.csv_validator import CSVValidator
from core.exceptions import ValidationError, SecurityViolationError
from services.import_service import ImportService
from database.connection import DatabaseConnection
from database.repositories import AppRepository

class TestCSVImport(unittest.TestCase):
    """Test suite validating CSV validation, PII redaction, and import workflows."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = DatabaseConnection(self.temp_file.name)
        self.db.initialize_schema()
        
        # Seed test app
        app_repo = AppRepository(self.db)
        app_repo.sync_from_config([{
            "internal_id": "test_groww",
            "official_name": "Groww Test App",
            "developer_name": "Groww Devs",
            "role": "primary_case_study",
            "apple_app_store": {"app_id": "111", "verification_status": "VERIFIED"},
            "google_play_store": {"package_name": "com.test.groww", "verification_status": "VERIFIED"}
        }])

        self.import_service = ImportService(self.db)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except Exception:
                pass

    def test_01_valid_csv_validation(self):
        """Verify that a properly structured review dataframe passes validation."""
        df = pd.DataFrame([
            {"review_text": "Smooth autopay setup for mutual fund.", "rating": 5, "review_date": "2026-10-01 10:00:00"},
            {"review_text": "Mandate deduction delayed by bank.", "rating": 2, "review_date": "2026-10-02 12:00:00"}
        ])
        res = CSVValidator.validate_and_clean_rows(df)
        self.assertEqual(res["accepted_count"], 2)
        self.assertEqual(res["rejected_count"], 0)

    def test_02_missing_required_column_raises_error(self):
        """Verify that missing review_text raises ValidationError."""
        df = pd.DataFrame([
            {"rating": 5, "review_date": "2026-10-01"}
        ])
        with self.assertRaises(ValidationError):
            CSVValidator.validate_and_clean_rows(df)

    def test_03_disallowed_pii_columns_rejected(self):
        """Verify that CSVs containing user_name or phone_number headers are rejected."""
        df = pd.DataFrame([
            {"review_text": "Good app", "rating": 5, "review_date": "2026-10-01", "user_name": "JohnDoe"}
        ])
        with self.assertRaises(ValidationError) as ctx:
            CSVValidator.validate_and_clean_rows(df)
        self.assertIn("Privacy Violation", str(ctx.exception))

    def test_04_in_text_pii_sanitization(self):
        """Verify that phone numbers and email addresses in review text are sanitized."""
        text_with_pii = "Call me at +91 9876543210 or email test.user@gmail.com regarding my failed SIP."
        clean_text, redacted = CSVValidator.sanitize_text(text_with_pii)
        
        self.assertTrue(redacted)
        self.assertNotIn("9876543210", clean_text)
        self.assertNotIn("test.user@gmail.com", clean_text)
        self.assertIn("[PHONE_REDACTED]", clean_text)
        self.assertIn("[EMAIL_REDACTED]", clean_text)

    def test_05_unconfirmed_provenance_blocked(self):
        """Verify that unconfirmed legal provenance aborts import with SecurityViolationError."""
        df = pd.DataFrame([
            {"review_text": "Valid review text.", "rating": 5, "review_date": "2026-10-01"}
        ])
        temp_csv = tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False)
        df.to_csv(temp_csv.name, index=False)
        temp_csv.close()

        try:
            with self.assertRaises(SecurityViolationError):
                self.import_service.execute_import(
                    file_or_path=temp_csv.name,
                    filename="test.csv",
                    app_id="test_groww",
                    store="google_play",
                    permission_status="APPROVED",
                    provenance_confirmed=False  # Must fail
                )
        finally:
            if os.path.exists(temp_csv.name):
                os.remove(temp_csv.name)

    def test_06_rejected_permission_status_blocked(self):
        """Verify that source with REJECTED permission status is blocked."""
        df = pd.DataFrame([
            {"review_text": "Valid review text.", "rating": 5, "review_date": "2026-10-01"}
        ])
        temp_csv = tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False)
        df.to_csv(temp_csv.name, index=False)
        temp_csv.close()

        try:
            with self.assertRaises(SecurityViolationError):
                self.import_service.execute_import(
                    file_or_path=temp_csv.name,
                    filename="test.csv",
                    app_id="test_groww",
                    store="google_play",
                    permission_status="REJECTED",
                    provenance_confirmed=True
                )
        finally:
            if os.path.exists(temp_csv.name):
                os.remove(temp_csv.name)

if __name__ == "__main__":
    unittest.main()
