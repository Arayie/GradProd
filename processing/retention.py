"""
Retention Governance and Lifecycle Management for Growww Discovery Engine.
Implements Task 7: enforces source-specific retention limits (365 days),
evaluates expiry timestamps, manages quarantine states, and filters research-ready outputs.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

DEFAULT_RETENTION_DAYS = 365

SOURCE_RETENTION_POLICIES = {
    "apple_app_store_rss": {
        "retention_days": 365,
        "policy_version": "1.0.0",
        "description": "Public syndication feed; retained for 365 days from ingestion date for NLP research."
    },
    "manual_csv_import": {
        "retention_days": 365,
        "policy_version": "1.0.0",
        "description": "Public research archive CSV; retained for 365 days from ingestion date."
    },
    "google_play_publisher_api": {
        "retention_days": 730,
        "policy_version": "1.0.0",
        "description": "Owner API authorized data; retained for 730 days under enterprise research mandate."
    }
}

class RetentionManager:
    """Manages data retention periods, expiry checks, and deletion lifecycle."""

    def __init__(self, default_days: int = DEFAULT_RETENTION_DAYS):
        self.default_days = default_days
        self._deletion_audit_log: List[Dict[str, Any]] = []

    def compute_retention_expiry(
        self,
        retrieved_at: Any,
        collection_method: str = "apple_app_store_rss"
    ) -> Tuple[str, str]:
        """
        Calculates retention expiry UTC timestamp based on collection method.
        Returns: (expiry_timestamp_utc, policy_version)
        """
        policy = SOURCE_RETENTION_POLICIES.get(collection_method, {
            "retention_days": self.default_days,
            "policy_version": "1.0.0"
        })
        days = policy.get("retention_days", self.default_days)
        policy_ver = policy.get("policy_version", "1.0.0")

        # Parse retrieved_at
        dt_base = None
        if isinstance(retrieved_at, datetime):
            dt_base = retrieved_at
        elif isinstance(retrieved_at, str) and retrieved_at.strip():
            try:
                dt_base = datetime.strptime(retrieved_at[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt_base = datetime.utcnow()
        else:
            dt_base = datetime.utcnow()

        expiry_dt = dt_base + timedelta(days=days)
        return expiry_dt.strftime("%Y-%m-%d %H:%M:%S"), policy_ver

    def evaluate_lifecycle_status(
        self,
        record: Dict[str, Any],
        now_dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evaluates deletion_status, retention_expiry_at, and research eligibility.
        Status: 'ACTIVE', 'EXPIRED', 'QUARANTINED', or 'DELETED'.
        """
        enriched = dict(record)
        current_dt = now_dt or datetime.utcnow()
        method = record.get("collection_method", "apple_app_store_rss")
        retrieved_at = record.get("retrieved_at")

        # 1. Compute or verify retention_expiry_at
        expiry_str = record.get("retention_expiry_at")
        policy_ver = record.get("source_policy_version", "1.0.0")
        if not expiry_str:
            expiry_str, policy_ver = self.compute_retention_expiry(retrieved_at, method)

        enriched["retention_expiry_at"] = expiry_str
        enriched["source_policy_version"] = policy_ver

        # 2. Check existing deletion status
        current_status = record.get("deletion_status", "ACTIVE")
        if current_status == "DELETED":
            enriched["deletion_status"] = "DELETED"
            return enriched

        # 3. Check for source permission rejection or synthetic quarantine
        eligibility = record.get("eligibility_status", "ELIGIBLE")
        if eligibility == "SYNTHETIC_DEMO":
            enriched["deletion_status"] = "QUARANTINED"
            return enriched
        if eligibility == "REJECTED":
            enriched["deletion_status"] = "QUARANTINED"
            return enriched

        # 4. Check for timestamp expiry
        try:
            exp_dt = datetime.strptime(expiry_str[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
            if current_dt > exp_dt:
                enriched["deletion_status"] = "EXPIRED"
                return enriched
        except Exception:
            pass

        enriched["deletion_status"] = "ACTIVE"
        return enriched

    def is_eligible_for_research(self, record: Dict[str, Any]) -> bool:
        """
        Strict gatekeeper: determines whether a record can enter researcher-facing datasets.
        Must be ACTIVE, non-synthetic, ELIGIBLE, and not deleted/expired.
        """
        deletion_status = record.get("deletion_status", "ACTIVE")
        eligibility_status = record.get("eligibility_status", "ELIGIBLE")

        if deletion_status != "ACTIVE":
            return False
        if eligibility_status in ("SYNTHETIC_DEMO", "REJECTED", "PENDING"):
            return False
        return True

_retention_mgr = None

def get_retention_manager() -> RetentionManager:
    """Returns singleton instance of RetentionManager."""
    global _retention_mgr
    if _retention_mgr is None:
        _retention_mgr = RetentionManager()
    return _retention_mgr
