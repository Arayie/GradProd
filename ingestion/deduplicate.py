"""
Deduplication and Idempotency Engine for Growww Discovery Engine.
Enforces deduplication priority:
1. Stable source review ID (source_record_id)
2. Store + App ID + Source Record ID
3. Canonical SHA-256 content hash of normalized review text when ID is unavailable.
"""
import os
import sys
import hashlib
from typing import Dict, Any, Optional

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if os.path.exists(LIB_DIR) and LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.repositories import ReviewRepository
from database.connection import DatabaseConnection

def compute_canonical_content_hash(text: str) -> str:
    """Computes a SHA-256 hash of whitespace-normalized lowercase review text."""
    if not text:
        return ""
    normalized = " ".join(text.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class Deduplicator:
    """Manages review deduplication checking against persistent storage and in-memory caches."""

    def __init__(self, review_repo: Any = None):
        if isinstance(review_repo, DatabaseConnection):
            self.review_repo = ReviewRepository(review_repo)
        elif isinstance(review_repo, ReviewRepository):
            self.review_repo = review_repo
        else:
            self.review_repo = ReviewRepository()
        self._seen_in_batch_ids = set()
        self._seen_in_batch_hashes = set()

    def reset_batch_cache(self):
        """Clears in-memory cache for a new collection run."""
        self._seen_in_batch_ids.clear()
        self._seen_in_batch_hashes.clear()

    def is_duplicate(
        self,
        app_id: str,
        store: str,
        source_record_id: Optional[str] = None,
        content_hash: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> bool:
        """
        Determines whether a review already exists in the current batch or persistent database.
        Returns True if duplicate, False if unique.
        """
        if not content_hash and raw_text:
            content_hash = compute_canonical_content_hash(raw_text)

        # 1. In-batch check for source_record_id
        if source_record_id:
            batch_key = f"{app_id}:{store}:{source_record_id}"
            if batch_key in self._seen_in_batch_ids:
                return True

        # 2. In-batch check for content_hash
        if content_hash:
            batch_hash_key = f"{app_id}:{store}:{content_hash}"
            if batch_hash_key in self._seen_in_batch_hashes:
                return True

        # 3. Database check
        is_in_db = self.review_repo.exists(
            app_id=app_id,
            store=store,
            source_record_id=source_record_id,
            content_hash=content_hash
        )

        return is_in_db

    def mark_seen(
        self,
        app_id: str,
        store: str,
        source_record_id: Optional[str] = None,
        content_hash: Optional[str] = None,
        raw_text: Optional[str] = None
    ):
        """Marks a record as seen within the active batch context."""
        if not content_hash and raw_text:
            content_hash = compute_canonical_content_hash(raw_text)
        if source_record_id:
            self._seen_in_batch_ids.add(f"{app_id}:{store}:{source_record_id}")
        if content_hash:
            self._seen_in_batch_hashes.add(f"{app_id}:{store}:{content_hash}")

ReviewDeduplicator = Deduplicator

_deduplicator = None

def get_deduplicator(db: Optional[DatabaseConnection] = None) -> Deduplicator:
    """Returns singleton Deduplicator instance."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = Deduplicator(db)
    return _deduplicator
