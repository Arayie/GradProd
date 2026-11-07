"""
Advanced Multi-Tier Deduplication and Near-Duplicate Screening for Growww Discovery Engine.
Implements Task 6: verifies source record ID idempotency, store-composite keys,
exact SHA-256 normalized content hashing, and conservative near-duplicate clustering.
"""
import os
import sys
import re
import hashlib
from typing import Dict, Any, List, Set, Optional, Tuple

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from ingestion.deduplicate import compute_canonical_content_hash

def get_word_tokens(text: str) -> Set[str]:
    """Generates unique word tokens from normalized text for similarity matching."""
    return {w for w in re.findall(r"\b\w+\b", text.lower()) if len(w) > 1}

def get_word_ngrams(text: str, n: int = 2) -> Set[str]:
    """Generates word n-grams from normalized text for similarity matching."""
    words = [w for w in re.findall(r"\b\w+\b", text.lower()) if len(w) > 1]
    if len(words) < n:
        return {" ".join(words)}
    return {" ".join(words[i:i+n]) for i in range(len(words) - n + 1)}

def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculates Jaccard similarity index between two token or n-gram sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0

class AdvancedDeduplicator:
    """Multi-tier deduplicator enforcing exact identity constraints and near-duplicate candidate detection."""

    def __init__(self, near_duplicate_threshold: float = 0.85):
        self.threshold = near_duplicate_threshold
        # In-memory tracking of processed keys
        self._seen_source_ids: Dict[Tuple[str, str, str], str] = {}  # (app, store, src_id) -> evidence_id
        self._seen_content_hashes: Dict[Tuple[str, str, str], str] = {}  # (app, store, hash) -> evidence_id
        self._recent_records: List[Dict[str, Any]] = []

    def reset(self):
        """Resets in-memory deduplication state."""
        self._seen_source_ids.clear()
        self._seen_content_hashes.clear()
        self._recent_records.clear()

    def evaluate_record(
        self,
        record: Dict[str, Any],
        existing_lookup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates duplicate status for a review record against known keys and historical records.
        Assigns dedupe_group_id, duplicate_status, duplicate_of_evidence_id, and deduplication_method.
        """
        app_id = record.get("app_id", "unknown")
        store = record.get("store", "unknown")
        source_id = str(record.get("source_record_id") or "").strip()
        content_hash = record.get("content_hash") or compute_canonical_content_hash(record.get("review_text", ""))
        evidence_id = record.get("evidence_id")
        text = record.get("review_text", "")

        enriched = dict(record)
        enriched["content_hash"] = content_hash

        # Tier 1: Check Exact Source ID (app, store, source_record_id)
        if source_id:
            key_src = (app_id, store, source_id)
            if key_src in self._seen_source_ids:
                prior_evidence = self._seen_source_ids[key_src]
                enriched["duplicate_status"] = "DUPLICATE_SOURCE_ID"
                enriched["duplicate_of_evidence_id"] = prior_evidence
                enriched["deduplication_method"] = "source_id_exact"
                enriched["dedupe_group_id"] = f"GRP_{prior_evidence}"
                return enriched

        # Tier 2: Check Exact Content Hash (app, store, content_hash)
        key_hash = (app_id, store, content_hash)
        if key_hash in self._seen_content_hashes:
            prior_evidence = self._seen_content_hashes[key_hash]
            enriched["duplicate_status"] = "DUPLICATE_HASH"
            enriched["duplicate_of_evidence_id"] = prior_evidence
            enriched["deduplication_method"] = "content_hash_exact"
            enriched["dedupe_group_id"] = f"GRP_{prior_evidence}"
            return enriched

        # Tier 3: Conservative Near-Duplicate Candidate Detection (Length > 30 chars)
        if len(text) >= 30 and self._recent_records:
            current_tokens = get_word_tokens(text)
            current_ngrams = get_word_ngrams(text, n=2)
            for prior in reversed(self._recent_records[-200:]):  # check against rolling buffer
                if prior.get("app_id") != app_id or prior.get("store") != store:
                    continue
                prior_text = prior.get("review_text", "")
                if abs(len(text) - len(prior_text)) > 40:
                    continue
                prior_tokens = get_word_tokens(prior_text)
                sim_tok = jaccard_similarity(current_tokens, prior_tokens)
                sim_ngr = jaccard_similarity(current_ngrams, get_word_ngrams(prior_text, n=2))
                effective_sim = max(sim_tok, sim_ngr)
                if effective_sim >= self.threshold:
                    prior_evidence = prior.get("evidence_id")
                    enriched["duplicate_status"] = "NEAR_DUPLICATE_CANDIDATE"
                    enriched["duplicate_of_evidence_id"] = prior_evidence
                    enriched["deduplication_method"] = f"similarity_{effective_sim:.2f}"
                    enriched["dedupe_group_id"] = f"GRP_{prior_evidence}"
                    # Note: We do NOT merge or discard near-duplicate candidates
                    # Record is retained with candidate flag for analyst inspection
                    return enriched

        # Record is UNIQUE
        if source_id:
            self._seen_source_ids[(app_id, store, source_id)] = evidence_id
        self._seen_content_hashes[(app_id, store, content_hash)] = evidence_id
        self._recent_records.append({"app_id": app_id, "store": store, "review_text": text, "evidence_id": evidence_id})

        enriched["duplicate_status"] = "UNIQUE"
        enriched["duplicate_of_evidence_id"] = None
        enriched["deduplication_method"] = "none"
        enriched["dedupe_group_id"] = f"GRP_{evidence_id}"
        return enriched

_deduplicator = None

def get_advanced_deduplicator() -> AdvancedDeduplicator:
    """Returns singleton instance of AdvancedDeduplicator."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = AdvancedDeduplicator()
    return _deduplicator
