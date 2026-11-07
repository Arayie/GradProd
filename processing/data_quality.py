"""
Data Quality Assessment and Scoring for Growww Discovery Engine.
Implements Task 8: evaluates source provenance completeness, text validity,
date integrity, language confidence, PII status, and produces normalized quality scores.
"""
import json
from typing import Dict, Any, List, Tuple

class DataQualityScorer:
    """Evaluates data quality dimensions across completeness, validity, and governance."""

    # Weighted scoring dimensions (Total 100 points -> 1.0)
    WEIGHTS = {
        "provenance_complete": 0.15,      # Evidence ID, source permission, collection run
        "app_store_valid": 0.15,          # Recognized app and store
        "text_meaningful": 0.20,          # Non-empty, reasonable length (>10 chars)
        "date_valid": 0.10,               # Valid UTC creation timestamp
        "rating_valid": 0.10,             # Valid rating 1-5
        "language_confidence": 0.10,      # Language confidence >= 0.60
        "pii_clean": 0.10,                # PII sanitized or clean
        "retention_valid": 0.10           # Active deletion status, non-expired
    }

    def assess_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates data_quality_score, data_quality_status, and data_quality_issues.
        Statuses:
          - 'BLOCKED': Invalid permission, expired, or synthetic/rejected.
          - 'HIGH_QUALITY': Score >= 0.85 with no critical flaws.
          - 'ACCEPTABLE': Score between 0.60 and 0.84.
          - 'LOW_QUALITY': Score < 0.60 (e.g. extremely short text, missing metadata).
        """
        score = 0.0
        issues = []

        # 0. Check Hard Blocks
        eligibility = record.get("eligibility_status", "ELIGIBLE")
        deletion_status = record.get("deletion_status", "ACTIVE")
        if eligibility in ("REJECTED", "SYNTHETIC_DEMO") or deletion_status in ("EXPIRED", "DELETED", "QUARANTINED"):
            issues.append(f"GOVERNANCE_BLOCKED: eligibility={eligibility}, deletion={deletion_status}")
            return {
                "data_quality_score": 0.0,
                "data_quality_status": "BLOCKED",
                "data_quality_issues": json.dumps(issues)
            }

        # 1. Provenance completeness (15 pts)
        has_evidence = bool(record.get("evidence_id"))
        has_run = bool(record.get("collection_run_id"))
        has_perm = bool(record.get("source_permission_id"))
        if has_evidence and has_run and has_perm:
            score += self.WEIGHTS["provenance_complete"]
        else:
            if not has_evidence:
                issues.append("MISSING_EVIDENCE_ID")
            if not has_perm:
                issues.append("MISSING_PERMISSION_REF")

        # 2. App & Store validity (15 pts)
        has_app = bool(record.get("app_id") and record.get("app_id") != "unknown")
        has_store = record.get("store") in ("apple_app_store", "google_play")
        if has_app and has_store:
            score += self.WEIGHTS["app_store_valid"]
        else:
            if not has_app:
                issues.append("UNKNOWN_APP_ID")
            if not has_store:
                issues.append("INVALID_STORE_IDENTIFIER")

        # 3. Text completeness and substance (20 pts)
        text = str(record.get("review_text") or "").strip()
        word_count = len(text.split())
        if word_count >= 5 and len(text) >= 20:
            score += self.WEIGHTS["text_meaningful"]
        elif word_count >= 2:
            score += (self.WEIGHTS["text_meaningful"] * 0.6)
            issues.append("SHORT_TEXT_LOW_SUBSTANCE")
        else:
            issues.append("EMPTY_OR_TRIVIAL_TEXT")

        # 4. Date validity (10 pts)
        created_at = record.get("review_created_at")
        if created_at and len(str(created_at)) >= 10:
            score += self.WEIGHTS["date_valid"]
        else:
            issues.append("INVALID_OR_MISSING_DATE")

        # 5. Rating validity (10 pts)
        try:
            rating = int(record.get("star_rating", 0))
            if 1 <= rating <= 5:
                score += self.WEIGHTS["rating_valid"]
            else:
                issues.append("RATING_OUT_OF_BOUNDS")
        except (ValueError, TypeError):
            issues.append("INVALID_RATING_TYPE")

        # 6. Language detection confidence (10 pts)
        lang_conf = float(record.get("language_confidence", 0.0))
        lang = record.get("language_detected", "unknown")
        if lang != "unknown" and lang_conf >= 0.60:
            score += self.WEIGHTS["language_confidence"]
        elif lang_conf >= 0.40:
            score += (self.WEIGHTS["language_confidence"] * 0.5)
            issues.append("LOW_LANGUAGE_CONFIDENCE")
        else:
            issues.append("UNKNOWN_OR_UNCONFIDENT_LANGUAGE")

        # 7. PII Sanitization Status (10 pts)
        redaction_status = record.get("redaction_status", "CLEAN")
        if redaction_status in ("CLEAN", "REDACTED"):
            score += self.WEIGHTS["pii_clean"]
        else:
            issues.append("UNVERIFIED_PII_STATUS")

        # 8. Retention validity (10 pts)
        if deletion_status == "ACTIVE":
            score += self.WEIGHTS["retention_valid"]
        else:
            issues.append(f"NON_ACTIVE_RETENTION_{deletion_status}")

        final_score = round(min(1.0, max(0.0, score)), 2)

        # Status determination
        if final_score >= 0.85 and not any("EMPTY" in i or "MISSING_EVIDENCE" in i for i in issues):
            status = "HIGH_QUALITY"
        elif final_score >= 0.60:
            status = "ACCEPTABLE"
        else:
            status = "LOW_QUALITY"

        return {
            "data_quality_score": final_score,
            "data_quality_status": status,
            "data_quality_issues": json.dumps(issues)
        }

    def enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches record with data quality metrics."""
        assessment = self.assess_record(record)
        enriched = dict(record)
        enriched.update(assessment)
        return enriched

_scorer = None

def get_data_quality_scorer() -> DataQualityScorer:
    """Returns singleton instance of DataQualityScorer."""
    global _scorer
    if _scorer is None:
        _scorer = DataQualityScorer()
    return _scorer
