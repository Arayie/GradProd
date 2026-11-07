"""
CSV Import Service for Growww Discovery Engine.
Orchestrates CSV parsing, column mapping, row validation, provenance verification,
database transactions, and batch auditing.
"""
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import get_db, DatabaseConnection
from database.repositories import ReviewRepository, ImportBatchRepository
from core.csv_validator import CSVValidator
from core.exceptions import ValidationError, SecurityViolationError, DuplicateRecordError

class ImportService:
    """Service handling manual CSV review dataset ingestion with atomic transactions."""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or get_db()
        self.review_repo = ReviewRepository(self.db)
        self.batch_repo = ImportBatchRepository(self.db)

    def preview_csv(self, file_or_path: Any, nrows: int = 5) -> Dict[str, Any]:
        """Reads first nrows of CSV for UI preview and column mapping."""
        try:
            df = pd.read_csv(file_or_path, nrows=nrows)
            inspection = CSVValidator.inspect_dataframe(df)
            return {
                "success": True,
                "preview_df": df,
                "inspection": inspection,
                "error": None
            }
        except Exception as exc:
            return {
                "success": False,
                "preview_df": None,
                "inspection": None,
                "error": str(exc)
            }

    def execute_import(
        self,
        file_or_path: Any,
        filename: str,
        app_id: str,
        store: str,
        permission_status: str,
        provenance_confirmed: bool,
        source_description: str = "",
        column_mapping: Optional[Dict[str, str]] = None,
        is_synthetic: bool = False
    ) -> Dict[str, Any]:
        """
        Executes full validation and transactional persistence of CSV rows.
        """
        # Security & Permission Gate
        if not is_synthetic and not provenance_confirmed:
            raise SecurityViolationError(
                "Data Provenance Unconfirmed: You must confirm that the uploaded review dataset "
                "was legally obtained and complies with research privacy policies."
            )

        if permission_status == "REJECTED":
            raise SecurityViolationError("Import Aborted: The selected data source has a REJECTED permission status.")

        # Read complete dataframe
        try:
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
            df = pd.read_csv(file_or_path)
        except Exception as exc:
            raise ValidationError(f"Failed to read CSV file: {exc}") from exc

        # Validate rows
        validation_result = CSVValidator.validate_and_clean_rows(df, column_mapping=column_mapping)
        accepted_candidates = validation_result["accepted_rows"]
        rejected_rows = validation_result["rejected_rows"]

        # Determine review eligibility status
        if is_synthetic:
            eligibility = "SYNTHETIC_DEMO"
        elif permission_status == "APPROVED" and provenance_confirmed:
            eligibility = "ELIGIBLE"
        else:
            eligibility = "PENDING"

        batch_id = f"BATCH_{uuid.uuid4().hex[:8].upper()}_{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        
        # Initialize batch tracking in database
        self.batch_repo.create_batch({
            "batch_id": batch_id,
            "original_filename": filename,
            "app_id": app_id,
            "store": store,
            "source_description": source_description,
            "permission_status": permission_status,
            "total_rows": len(df),
            "batch_status": "PROCESSING"
        })

        accepted_count = 0
        duplicate_count = 0
        persisted_records = []

        # Execute transactional insert
        with self.db.get_connection():
            for row in accepted_candidates:
                # Check for duplicate in DB
                is_dup = self.review_repo.exists(
                    app_id=app_id,
                    store=store,
                    source_record_id=row.get("source_record_id"),
                    content_hash=row.get("content_hash")
                )
                if is_dup:
                    duplicate_count += 1
                    continue

                evidence_id = f"EV_{app_id[:4].upper()}_{store[:3].upper()}_{row['content_hash'][:8]}"
                record = {
                    "evidence_id": evidence_id,
                    "app_id": app_id,
                    "store": store,
                    "source_record_id": row.get("source_record_id"),
                    "canonical_url": row.get("canonical_url"),
                    "collection_run_id": batch_id,
                    "collection_method": "manual_csv_import",
                    "source_permission_id": f"PERM_{permission_status}",
                    "review_title": row.get("review_title"),
                    "review_text": row["review_text"],
                    "star_rating": row["star_rating"],
                    "review_created_at": row["review_created_at"],
                    "app_version": row.get("app_version"),
                    "language_original": row.get("language_original", "unknown"),
                    "content_hash": row["content_hash"],
                    "content_status": "ORIGINAL",
                    "redaction_status": row.get("redaction_status", "CLEAN"),
                    "storefront": "IN",
                    "eligibility_status": eligibility,
                    "provider_name": "Manual Import",
                    "deletion_status": "ACTIVE"
                }

                try:
                    self.review_repo.insert_review(record)
                    accepted_count += 1
                    persisted_records.append(record)
                except DuplicateRecordError:
                    duplicate_count += 1
                except Exception as exc:
                    rejected_rows.append({
                        "row_number": accepted_count + duplicate_count + len(rejected_rows) + 1,
                        "errors": [f"Database error: {exc}"],
                        "raw_data": row
                    })

        # Update final batch status
        final_status = "COMPLETED" if accepted_count > 0 or duplicate_count > 0 else "FAILED"
        self.batch_repo.update_batch_stats(
            batch_id=batch_id,
            accepted=accepted_count,
            rejected=len(rejected_rows),
            duplicates=duplicate_count,
            status=final_status
        )

        return {
            "batch_id": batch_id,
            "total_rows": len(df),
            "accepted_count": accepted_count,
            "rejected_count": len(rejected_rows),
            "duplicate_count": duplicate_count,
            "eligibility_status": eligibility,
            "rejected_rows_details": rejected_rows
        }

_import_service = None

def get_import_service() -> ImportService:
    """Returns singleton instance of ImportService."""
    global _import_service
    if _import_service is None:
        _import_service = ImportService()
    return _import_service
