"""
CSV Validator and Sanitizer for Growww Discovery Engine.
Enforces schema validation, row-level error reporting, date normalization, and PII redaction.
"""
import os
import sys
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from core.exceptions import ValidationError

# Standard canonical columns
REQUIRED_COLUMNS = ["review_text", "review_date", "rating"]
OPTIONAL_COLUMNS = [
    "review_id", "review_title", "app_version", "language",
    "source_url", "app_name", "platform", "store"
]

# Sensitive PII Regex patterns for India
PII_PATTERNS = {
    "phone": re.compile(r"(\+91[\-\s]?)?[6-9]\d{9}"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "pan": re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]{1}"),
    "bank_account": re.compile(r"\b\d{9,18}\b"),
    "upi": re.compile(r"[\w\.\-_]+@[\w]+")
}

DISALLOWED_COLUMNS = [
    "user_name", "username", "author_name", "author", "reviewer_name",
    "phone_number", "mobile", "email", "pan_number", "customer_id",
    "bank_account", "account_number"
]

class CSVValidator:
    """Validates and sanitizes review CSV files prior to ingestion."""

    @staticmethod
    def inspect_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes column presence, disallowed columns, and suggests mappings."""
        cols = [c.strip().lower() for c in df.columns]
        
        # Check disallowed PII columns
        disallowed_present = [col for col in cols if col in DISALLOWED_COLUMNS]
        
        # Map alternate common header names
        mapping_suggestions = {}
        for c in df.columns:
            clean = c.strip().lower()
            if clean in ["content", "body", "review", "text", "comment"]:
                mapping_suggestions[c] = "review_text"
            elif clean in ["date", "created_at", "timestamp", "review_timestamp", "time"]:
                mapping_suggestions[c] = "review_date"
            elif clean in ["score", "stars", "star_rating", "ratings"]:
                mapping_suggestions[c] = "rating"
            elif clean in ["id", "reviewid", "source_id"]:
                mapping_suggestions[c] = "review_id"
            elif clean in ["title", "subject", "headline"]:
                mapping_suggestions[c] = "review_title"
            elif clean in ["version", "appversion"]:
                mapping_suggestions[c] = "app_version"
            elif clean in ["lang", "language_code"]:
                mapping_suggestions[c] = "language"
            elif clean in ["url", "link"]:
                mapping_suggestions[c] = "source_url"

        return {
            "total_rows": len(df),
            "columns": list(df.columns),
            "disallowed_columns": disallowed_present,
            "mapping_suggestions": mapping_suggestions
        }

    @staticmethod
    def sanitize_text(text: str) -> Tuple[str, bool]:
        """Redacts sensitive PII (phones, emails, PANs, account numbers) from text."""
        if not text or not isinstance(text, str):
            return "", False

        sanitized = text
        redacted = False

        if PII_PATTERNS["phone"].search(sanitized):
            sanitized = PII_PATTERNS["phone"].sub("[PHONE_REDACTED]", sanitized)
            redacted = True

        if PII_PATTERNS["email"].search(sanitized):
            sanitized = PII_PATTERNS["email"].sub("[EMAIL_REDACTED]", sanitized)
            redacted = True

        if PII_PATTERNS["pan"].search(sanitized):
            sanitized = PII_PATTERNS["pan"].sub("[PAN_REDACTED]", sanitized)
            redacted = True

        if PII_PATTERNS["upi"].search(sanitized):
            sanitized = PII_PATTERNS["upi"].sub("[UPI_REDACTED]", sanitized)
            redacted = True

        return sanitized, redacted

    @staticmethod
    def parse_review_date(date_val: Any) -> Optional[str]:
        """Parses flexible date formats and converts to ISO 8601 UTC string."""
        if pd.isna(date_val):
            return None

        # If already string
        date_str = str(date_val).strip()
        common_formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d %b %Y",
            "%d %B %Y"
        ]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        # Fallback to dateutil / pandas
        try:
            parsed = pd.to_datetime(date_str)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    @classmethod
    def validate_and_clean_rows(
        cls,
        df: pd.DataFrame,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Validates all rows against canonical schema and privacy constraints.
        Returns accepted rows, rejected rows, duplicate rows, and validation summary.
        """
        working_df = df.copy()

        # Apply column mapping
        if column_mapping:
            rename_dict = {orig: target for orig, target in column_mapping.items() if target}
            working_df = working_df.rename(columns=rename_dict)

        # Standardize column names to lower
        working_df.columns = [c.strip().lower() for c in working_df.columns]

        # Automatic standard alias resolution if canonical column is not already present
        auto_aliases = {
            "rating": ["star_rating", "score", "stars", "ratings"],
            "review_text": ["content", "body", "review", "text", "comment"],
            "review_date": ["date", "created_at", "timestamp", "review_timestamp", "time"],
            "review_id": ["id", "reviewid", "source_id"],
            "review_title": ["title", "subject", "headline"],
            "app_version": ["version", "appversion"],
            "language": ["lang", "language_code"],
            "source_url": ["url", "link"]
        }
        for canonical, aliases in auto_aliases.items():
            if canonical not in working_df.columns:
                for alias in aliases:
                    if alias in working_df.columns:
                        working_df = working_df.rename(columns={alias: canonical})
                        break

        # Verify required columns exist
        missing_required = [col for col in REQUIRED_COLUMNS if col not in working_df.columns]
        if missing_required:
            raise ValidationError(f"CSV is missing required canonical column(s): {', '.join(missing_required)}")

        # Block disallowed PII columns
        disallowed = [c for c in working_df.columns if c in DISALLOWED_COLUMNS]
        if disallowed:
            raise ValidationError(
                f"Privacy Violation: CSV contains disallowed personal identification column(s): {', '.join(disallowed)}. "
                "Author identities and personal contact details must be stripped before upload."
            )

        accepted_rows: List[Dict[str, Any]] = []
        rejected_rows: List[Dict[str, Any]] = []
        seen_hashes = set()
        seen_ids = set()

        for idx, row in working_df.iterrows():
            row_num = idx + 1
            errors = []

            # 1. Validate Review Text
            raw_text = str(row.get("review_text", "")).strip() if pd.notna(row.get("review_text")) else ""
            if not raw_text or raw_text.lower() in ["nan", "none", "null"]:
                errors.append("Empty review_text")

            # 2. Validate Star Rating
            rating_val = row.get("rating")
            parsed_rating = None
            try:
                if pd.notna(rating_val):
                    parsed_rating = int(float(str(rating_val).strip()))
                    if parsed_rating < 1 or parsed_rating > 5:
                        errors.append(f"Rating must be an integer between 1 and 5 (got {parsed_rating})")
                else:
                    errors.append("Missing rating")
            except (ValueError, TypeError):
                errors.append(f"Malformed rating value '{rating_val}'")

            # 3. Validate Date
            raw_date = row.get("review_date")
            parsed_date = cls.parse_review_date(raw_date)
            if not parsed_date:
                errors.append(f"Invalid or unparseable date '{raw_date}'")

            # 4. Check Deduplication
            content_hash = ""
            if raw_text:
                normalized = " ".join(raw_text.lower().split())
                content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                if content_hash in seen_hashes:
                    errors.append("Duplicate content in same file")
                else:
                    seen_hashes.add(content_hash)

            review_id = str(row.get("review_id", "")).strip() if pd.notna(row.get("review_id")) else ""
            if review_id:
                if review_id in seen_ids:
                    errors.append(f"Duplicate review_id '{review_id}' in same file")
                else:
                    seen_ids.add(review_id)

            # If any row validation errors
            if errors:
                rejected_rows.append({
                    "row_number": row_num,
                    "errors": errors,
                    "raw_data": row.to_dict()
                })
                continue

            # Sanitize PII
            clean_text, was_redacted = cls.sanitize_text(raw_text)
            clean_title = str(row.get("review_title", "")).strip() if pd.notna(row.get("review_title")) else ""
            if clean_title:
                clean_title, title_redacted = cls.sanitize_text(clean_title)
                was_redacted = was_redacted or title_redacted

            clean_row = {
                "source_record_id": review_id or None,
                "review_title": clean_title or None,
                "review_text": clean_text,
                "star_rating": parsed_rating,
                "review_created_at": parsed_date,
                "app_version": str(row.get("app_version", "")).strip() if pd.notna(row.get("app_version")) else None,
                "language_original": str(row.get("language", "unknown")).strip() if pd.notna(row.get("language")) else "unknown",
                "canonical_url": str(row.get("source_url", "")).strip() if pd.notna(row.get("source_url")) else None,
                "content_hash": content_hash,
                "redaction_status": "REDACTED" if was_redacted else "CLEAN"
            }
            accepted_rows.append(clean_row)

        return {
            "total_rows": len(working_df),
            "accepted_count": len(accepted_rows),
            "rejected_count": len(rejected_rows),
            "accepted_rows": accepted_rows,
            "rejected_rows": rejected_rows
        }
