"""
Canonical Data Standardization and Normalization for Growww Discovery Engine.
Implements Task 1: standardizes text formatting, HTML decoding, Unicode NFKC,
date parsing to UTC, rating validation, and canonical field alignment across
both Apple App Store and Google Play Store reviews.
"""
import os
import sys
import re
import html
import unicodedata
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from ingestion.deduplicate import compute_canonical_content_hash
from core.config_loader import get_config_loader

class ReviewNormalizer:
    """Standardizes heterogeneous review payloads from Apple and Google Play."""

    # Pre-compiled HTML tag remover
    HTML_TAG_RE = re.compile(r"<[^>]+>")
    # Multi-whitespace compressor
    MULTI_SPACE_RE = re.compile(r"[ \t\r\f\v]+")
    # Multi-newline compressor
    MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

    STORE_ALIASES = {
        "apple": "apple_app_store",
        "apple_app_store": "apple_app_store",
        "ios": "apple_app_store",
        "itunes": "apple_app_store",
        "google": "google_play",
        "google_play": "google_play",
        "android": "google_play",
        "play_store": "google_play"
    }

    def __init__(self, config_loader=None):
        self.config_loader = config_loader or get_config_loader()
        self._app_cache = {}
        self._load_app_metadata()

    def _load_app_metadata(self):
        """Loads registered applications to enrich canonical names and package identifiers."""
        try:
            apps = self.config_loader.get_registered_apps()
            for a in apps:
                app_id = a.get("internal_id")
                official_name = a.get("official_name")
                play_pkg = a.get("google_play_store", {}).get("package_name")
                apple_id = a.get("apple_app_store", {}).get("app_id")
                self._app_cache[app_id] = {
                    "app_name": official_name,
                    "package_name": play_pkg,
                    "apple_app_id": apple_id
                }
        except Exception:
            pass

    @classmethod
    def clean_text(cls, text: Optional[str]) -> Tuple[str, bool]:
        """
        Applies canonical text normalization:
        1. HTML entity unescaping (&amp; -> &, &#39; -> ', etc.)
        2. Safe HTML tag stripping (<p>, <br>, etc.)
        3. Unicode normalization (NFKC)
        4. Whitespace cleanup without destroying intended paragraph breaks
        Returns: (normalized_text, is_empty_flag)
        """
        if text is None:
            return "", True

        if not isinstance(text, str):
            text = str(text)

        # 1. Unescape HTML entities
        cleaned = html.unescape(text)

        # 2. Strip HTML tags
        cleaned = cls.HTML_TAG_RE.sub(" ", cleaned)

        # 3. Unicode normalization (NFKC decomposes compatibility chars & standardizes)
        cleaned = unicodedata.normalize("NFKC", cleaned)
        # Strip invisible zero-width formatting characters (\u200B-\u200D, \uFEFF)
        cleaned = re.sub(r"[\u200B-\u200D\uFEFF]", "", cleaned)

        # 4. Normalize spaces and excessive newlines
        cleaned = cls.MULTI_SPACE_RE.sub(" ", cleaned)
        cleaned = cls.MULTI_NEWLINE_RE.sub("\n\n", cleaned)
        cleaned = cleaned.strip()

        is_empty = len(cleaned) == 0
        return cleaned, is_empty

    @classmethod
    def parse_utc_timestamp(cls, ts_val: Any) -> Optional[str]:
        """
        Converts diverse date representations (ISO-8601 with timezone offsets,
        standard strings, epoch timestamps) to canonical UTC string: YYYY-MM-DD HH:MM:SS.
        """
        if not ts_val:
            return None

        if isinstance(ts_val, datetime):
            if ts_val.tzinfo:
                dt_utc = ts_val.astimezone(timezone.utc)
            else:
                dt_utc = ts_val
            return dt_utc.strftime("%Y-%m-%d %H:%M:%S")

        ts_str = str(ts_val).strip()
        if not ts_str:
            return None

        # Handle ISO-8601 timestamps like '2026-11-04T06:49:50-07:00' or '2026-11-04T06:49:50Z'
        try:
            clean_iso = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_iso)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        # Try common formats
        common_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%m/%d/%Y",
        ]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(ts_str[:19], fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

        # Fallback: return cleaned first 19 chars if sensible
        clean_fallback = ts_str.replace("T", " ")[:19]
        if len(clean_fallback) == 19 and clean_fallback[4] == "-" and clean_fallback[7] == "-":
            return clean_fallback

        return ts_str

    @classmethod
    def validate_rating(cls, rating_val: Any) -> Tuple[int, bool]:
        """
        Validates star rating is an integer between 1 and 5.
        Returns: (validated_rating, is_valid_flag)
        """
        try:
            val = int(float(rating_val))
            if 1 <= val <= 5:
                return val, True
            # Clamp or flag invalid
            clamped = max(1, min(5, val))
            return clamped, False
        except (ValueError, TypeError):
            return 3, False

    def normalize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardizes an individual raw review dictionary into canonical schema format.
        Preserves original raw text in review_text_original.
        """
        normalized = dict(raw_record)

        # 1. Store standardization
        raw_store = str(raw_record.get("store") or "").lower().strip()
        canonical_store = self.STORE_ALIASES.get(raw_store, raw_store or "unknown_store")
        normalized["store"] = canonical_store

        # 2. App identifiers & metadata lookup
        app_id = str(raw_record.get("app_id") or "").lower().strip()
        normalized["app_id"] = app_id
        app_meta = self._app_cache.get(app_id, {})
        normalized["app_name"] = raw_record.get("app_name") or app_meta.get("app_name")
        normalized["package_name"] = raw_record.get("package_name") or app_meta.get("package_name")

        # 3. Content standardization & original text preservation
        raw_text = raw_record.get("review_text_original") or raw_record.get("review_text") or ""
        normalized["review_text_original"] = str(raw_text)

        cleaned_text, is_empty = self.clean_text(raw_text)
        normalized["review_text"] = cleaned_text
        if is_empty:
            normalized["content_status"] = "EMPTY"
        else:
            normalized["content_status"] = "NORMALIZED"

        # Title normalization
        raw_title = raw_record.get("review_title")
        if raw_title:
            cleaned_title, _ = self.clean_text(raw_title)
            normalized["review_title"] = cleaned_title or None
        else:
            normalized["review_title"] = None

        # Content hash
        normalized["content_hash"] = compute_canonical_content_hash(cleaned_text)

        # 4. Rating validation
        validated_rating, is_rating_valid = self.validate_rating(raw_record.get("star_rating"))
        normalized["star_rating"] = validated_rating

        # 5. Timestamp standardization
        normalized["review_created_at"] = self.parse_utc_timestamp(raw_record.get("review_created_at"))
        normalized["review_updated_at"] = self.parse_utc_timestamp(raw_record.get("review_updated_at"))
        normalized["retrieved_at"] = self.parse_utc_timestamp(raw_record.get("retrieved_at")) or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 6. Store metadata
        normalized["storefront"] = (raw_record.get("storefront") or "IN").upper()
        normalized["app_version"] = raw_record.get("app_version") or None
        normalized["developer_reply_present"] = int(bool(raw_record.get("developer_reply_present", 0)))
        normalized["provider_name"] = raw_record.get("provider_name") or None
        normalized["store_listing_url"] = raw_record.get("store_listing_url") or None
        normalized["provider_limit_snapshot"] = raw_record.get("provider_limit_snapshot") or None

        # 7. Governance defaults
        normalized["eligibility_status"] = raw_record.get("eligibility_status") or "ELIGIBLE"
        normalized["source_policy_version"] = raw_record.get("source_policy_version") or "1.0.0"
        normalized["deletion_status"] = raw_record.get("deletion_status") or "ACTIVE"
        normalized["source_permission_id"] = raw_record.get("source_permission_id") or "PHASE0-AUDIT-APPROVED"

        # Evidence ID standard format: EV_{APP[:4]}_{STORE[:3]}_{HASH[:8]}
        if not raw_record.get("evidence_id"):
            prefix_app = app_id[:4].upper() if app_id else "UNKN"
            prefix_store = canonical_store[:3].upper() if canonical_store else "ST"
            normalized["evidence_id"] = f"EV_{prefix_app}_{prefix_store}_{normalized['content_hash'][:8]}"

        return normalized

_normalizer = None

def get_normalizer() -> ReviewNormalizer:
    """Returns singleton instance of ReviewNormalizer."""
    global _normalizer
    if _normalizer is None:
        _normalizer = ReviewNormalizer()
    return _normalizer
