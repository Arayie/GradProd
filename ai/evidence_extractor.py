"""
Exact Evidence Span Extractor and Grounding Verifier
Validates exact verbatim text spans against source review text.
Ensures 100% direct evidence grounding for research publications.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import string

class EvidenceExtractor:
    """Verifies and extracts exact verbatim substrings from review text for classification labels."""

    PUNCTUATION_TO_STRIP = string.punctuation + '""\'\'`«»‹›'

    @staticmethod
    def clean_span(span: Optional[str]) -> Optional[str]:
        """Strip surrounding quotes and whitespace from an extracted candidate span."""
        if not span:
            return None
        cleaned = span.strip()
        cleaned = cleaned.strip(EvidenceExtractor.PUNCTUATION_TO_STRIP).strip()
        return cleaned if cleaned else None

    @classmethod
    def find_exact_span(
        cls, candidate_span: Optional[str], text: str, fallback_text: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[int], Optional[int]]:
        """
        Check if candidate_span exists as an exact verbatim substring in text.
        Returns (is_match, exact_matched_span, start_char, end_char).
        """
        if not candidate_span or not text:
            return False, None, None, None

        cleaned = candidate_span.strip()
        if not cleaned:
            return False, None, None, None

        # 1. Exact match in primary text
        idx = text.find(cleaned)
        if idx != -1:
            return True, cleaned, idx, idx + len(cleaned)

        # 2. Match with punctuation stripped
        trimmed = cls.clean_span(cleaned)
        if trimmed and trimmed in text:
            idx = text.find(trimmed)
            return True, trimmed, idx, idx + len(trimmed)

        # 3. Case-insensitive exact match recovery (recover exact casing from original text)
        lower_text = text.lower()
        if trimmed and trimmed.lower() in lower_text:
            idx = lower_text.find(trimmed.lower())
            exact_original = text[idx : idx + len(trimmed)]
            return True, exact_original, idx, idx + len(trimmed)

        # 4. Try fallback text (e.g. unredacted or original text if different)
        if fallback_text:
            idx = fallback_text.find(cleaned)
            if idx != -1:
                return True, cleaned, idx, idx + len(cleaned)
            if trimmed and trimmed in fallback_text:
                idx = fallback_text.find(trimmed)
                return True, trimmed, idx, idx + len(trimmed)

        return False, None, None, None

    @classmethod
    def verify_and_ground_spans(
        cls,
        evidence_spans: Dict[str, Any],
        review_text: str,
        original_text: Optional[str] = None,
        assigned_labels: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, Optional[str]], str, Dict[str, Any]]:
        """
        Verify all candidate evidence spans against the review text.
        Returns:
            (verified_spans, grounding_status, grounding_metadata)
        """
        verified_spans: Dict[str, Optional[str]] = {}
        span_offsets: Dict[str, Tuple[int, int]] = {}
        matched_count = 0
        unmatched_count = 0
        null_count = 0

        neutral_labels = {
            "UNKNOWN",
            "NOT_STATED",
            "NO_PAIN_POINT_STATED",
            "IRRELEVANT",
            "OTHER_INTENT",
            "OTHER_EXPECTATION",
            "OTHER_BEHAVIOUR",
            "OTHER_TRIGGER",
            "OTHER_WORKAROUND",
        }

        for label, raw_span in evidence_spans.items():
            if raw_span is None or str(raw_span).strip().lower() in ("null", "none", ""):
                verified_spans[label] = None
                null_count += 1
                continue

            span_str = str(raw_span).strip()
            is_match, exact_span, start, end = cls.find_exact_span(
                span_str, review_text, fallback_text=original_text
            )

            if is_match and exact_span:
                verified_spans[label] = exact_span
                span_offsets[label] = (start, end)
                matched_count += 1
            else:
                # Discard hallucinated/non-verbatim quote
                verified_spans[label] = None
                unmatched_count += 1

        # Determine overall grounding status
        total_substantive = matched_count + unmatched_count
        if total_substantive == 0:
            grounding_status = "NO_EVIDENCE_STATED"
        elif unmatched_count == 0:
            grounding_status = "FULLY_GROUNDED"
        elif matched_count > 0:
            grounding_status = "PARTIALLY_GROUNDED"
        else:
            grounding_status = "UNSUPPORTED"

        grounding_metadata = {
            "total_candidate_spans": len(evidence_spans),
            "matched_exact_spans": matched_count,
            "unmatched_spans": unmatched_count,
            "null_spans": null_count,
            "span_offsets": span_offsets,
            "grounding_ratio": round(matched_count / max(1, total_substantive), 3),
        }

        return verified_spans, grounding_status, grounding_metadata
