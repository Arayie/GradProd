"""
Manual Review CSV Ingestion and Google Play Modular Ingestion Interface.
Handles CSV file loading, column aliasing, provenance tracking, and provides
modular extension points for future owner-authorized routes.
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

from core.csv_validator import CSVValidator
from core.exceptions import ValidationError, SecurityViolationError, SourcePermissionError

class ManualReviewCSVImporter:
    """Importer for manual CSV review datasets with data provenance enforcement."""

    def __init__(self):
        pass

    def inspect_file(self, file_or_path: Any, nrows: int = 5) -> Dict[str, Any]:
        """Inspects CSV structure and returns preview and suggested column mappings."""
        try:
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
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

    def parse_dataset(
        self,
        file_or_path: Any,
        filename: str,
        app_id: str,
        store: str,
        provenance_confirmed: bool,
        permission_status: str = "PENDING_VERIFICATION",
        source_description: str = "",
        column_mapping: Optional[Dict[str, str]] = None,
        is_synthetic: bool = False
    ) -> Dict[str, Any]:
        """
        Parses full CSV file, enforces provenance gate, sanitizes PII, and returns clean records.
        """
        if not is_synthetic and not provenance_confirmed:
            raise SecurityViolationError(
                "Data Provenance Unconfirmed: You must confirm that the uploaded review dataset "
                "was legally obtained and complies with research privacy policies."
            )

        if permission_status == "REJECTED":
            raise SecurityViolationError("Import Aborted: The selected data source has a REJECTED permission status.")

        try:
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
            df = pd.read_csv(file_or_path)
        except Exception as exc:
            raise ValidationError(f"Failed to read CSV file: {exc}") from exc

        # Execute row validation & PII sanitization
        cleaned_result = CSVValidator.validate_and_clean_rows(df, column_mapping=column_mapping)
        accepted_rows = cleaned_result["accepted_rows"]
        rejected_rows = cleaned_result["rejected_rows"]

        # Assign research eligibility status based on provenance and permissions
        if is_synthetic:
            eligibility = "SYNTHETIC_DEMO"
        elif permission_status == "APPROVED" and provenance_confirmed:
            eligibility = "ELIGIBLE"
        else:
            eligibility = "PENDING"  # Quarantined until permission verified

        batch_id = f"BATCH_{uuid.uuid4().hex[:8].upper()}_{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Attach complete provenance metadata to each accepted review
        formatted_reviews = []
        for row in accepted_rows:
            content_hash = row["content_hash"]
            evidence_id = f"EV_{app_id[:4].upper()}_{store[:3].upper()}_{content_hash[:8]}"
            formatted_reviews.append({
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
                "content_hash": content_hash,
                "content_status": "ORIGINAL",
                "redaction_status": row.get("redaction_status", "CLEAN"),
                "storefront": "IN",
                "eligibility_status": eligibility,
                "provider_name": "Manual CSV Import",
                "retrieved_at": now_utc
            })

        return {
            "batch_id": batch_id,
            "filename": filename,
            "app_id": app_id,
            "store": store,
            "source_description": source_description,
            "permission_status": permission_status,
            "total_rows": len(df),
            "accepted_count": len(formatted_reviews),
            "rejected_count": len(rejected_rows),
            "eligibility_status": eligibility,
            "reviews": formatted_reviews,
            "rejected_rows_details": rejected_rows
        }


# =========================================================================
# Modular Extension Points for Future Google Play Owner-Authorized Routes
# =========================================================================

class GooglePlayPublisherConnector:
    """
    MODULAR EXTENSION POINT (Phase 2 Stub / Future Route C):
    Google Play Android Publisher API (v3) client for authenticated app owners.
    Requires Google Cloud service account JSON credentials with Play Console API access.
    """
    def __init__(self, credentials_path: Optional[str] = None, credentials: Optional[Any] = None):
        self.credentials_path = credentials_path
        self.credentials = credentials
        self.is_authorized = bool((credentials_path and os.path.exists(credentials_path)) or credentials)

    def fetch_reviews(self, package_name: str) -> List[Dict[str, Any]]:
        """Stub method for future owner-authorized collection."""
        if not self.is_authorized:
            raise SourcePermissionError(
                "OWNER_AUTHENTICATION_REQUIRED: Google Play Developer API requires authorized service account credentials. "
                "Route is currently UNAVAILABLE for competitor applications."
            )
        # Future implementation when owner credentials are provided
        return []


class GooglePlayConsoleCSVParser:
    """
    MODULAR EXTENSION POINT (Phase 2 Stub / Future Route D):
    Parser for monthly bulk review exports directly downloaded from Google Play Console.
    Available only to verified application owners.
    """
    def __init__(self):
        pass

    def parse(self, file_path: str, authorized_owner: bool = False, app_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parses Google Play Console native review export CSV schema with owner authorization check."""
        if not authorized_owner:
            raise SecurityViolationError(
                "OWNER_AUTHORIZATION_REQUIRED: Google Play Console CSV exports are only permitted for authorized application owners."
            )
        return self.parse_console_export(file_path=file_path, app_id=app_id or "unknown")

    def parse_console_export(self, file_path: str, app_id: str) -> List[Dict[str, Any]]:
        """Parses Google Play Console native review export CSV schema."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Console export file not found: {file_path}")
        # Maps Google Play Console native headers:
        # 'Package Name', 'App Version Code', 'Reviewer Language', 'Star Rating', 'Review Title', 'Review Text'
        return []
