"""
PII Minimization and Redaction Pipeline for Growww Discovery Engine.
Implements Task 5: detects and redacts emails, Indian phone numbers, PAN cards,
bank account numbers, and UPI handles while preserving surrounding research context.
"""
import re
import json
from datetime import datetime
from typing import Dict, Any, Tuple, List

# Indian Phone Number Regex (+91 prefix optional, starts with 6-9, followed by 9 digits, allows dashes/spaces)
PHONE_REGEX = re.compile(
    r"(?:(?:\+91|0091|0)[\s\-]?)?(?:[6-9]\d{4}[\s\-]?\d{5}|[6-9]\d{9})\b"
)

# Standard Email Regex
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Indian PAN Card Regex: 5 letters + 4 digits + 1 letter
PAN_REGEX = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"
)

# UPI Handle Regex: username@(okhdfcbank|oksbi|okaxis|okicici|paytm|ybl|apl|upi|axl|ibl|barodampay|icici|sbi|hdfcbank)
UPI_REGEX = re.compile(
    r"\b[a-zA-Z0-9.\-_]{2,}@(okhdfcbank|oksbi|okaxis|okicici|paytm|ybl|apl|upi|axl|ibl|barodampay|icici|sbi|hdfcbank|axisbank|kotak|postbank)\b",
    re.IGNORECASE
)

# Bank Account Numbers in contextual phrases (9 to 18 digits)
BANK_ACCOUNT_REGEX = re.compile(
    r"(?:a/?c\s*(?:no\.?|number)?|account\s*(?:no\.?|number)?|acc\s*no\.?)\s*[:#\-]?\s*(\d{9,18})\b",
    re.IGNORECASE
)

class PIIMinimizer:
    """Detects, logs, and redacts personal identifying information from review text."""

    def redact_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Redacts sensitive tokens with standard placeholders.
        Returns: (redacted_text, detected_categories)
        """
        if not text:
            return "", []

        redacted = text
        categories = []

        # 1. Redact Emails first (prevents UPI overlap)
        if EMAIL_REGEX.search(redacted):
            redacted = EMAIL_REGEX.sub("[EMAIL_REDACTED]", redacted)
            categories.append("email")

        # 2. Redact UPI handles
        if UPI_REGEX.search(redacted):
            redacted = UPI_REGEX.sub("[UPI_REDACTED]", redacted)
            categories.append("upi")

        # 3. Redact PAN Cards
        if PAN_REGEX.search(redacted):
            redacted = PAN_REGEX.sub("[PAN_REDACTED]", redacted)
            categories.append("pan")

        # 4. Redact Bank Account Numbers with context
        if BANK_ACCOUNT_REGEX.search(redacted):
            redacted = BANK_ACCOUNT_REGEX.sub("account [BANK_ACCOUNT_REDACTED]", redacted)
            categories.append("bank_account")

        # 5. Redact Indian Phone Numbers
        if PHONE_REGEX.search(redacted):
            redacted = PHONE_REGEX.sub("[PHONE_REDACTED]", redacted)
            categories.append("phone")

        return redacted, sorted(list(set(categories)))

    def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies PII redaction to review_text and review_title in the record.
        Maintains review_text_original for legal audit where permitted.
        """
        processed = dict(record)
        now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        original_text = record.get("review_text") or ""
        original_title = record.get("review_title") or ""

        redacted_text, text_cats = self.redact_text(original_text)
        redacted_title, title_cats = self.redact_text(original_title) if original_title else (None, [])

        all_cats = sorted(list(set(text_cats + title_cats)))
        is_redacted = len(all_cats) > 0

        # Update text field with redacted version
        processed["review_text"] = redacted_text
        if original_title:
            processed["review_title"] = redacted_title

        # Set PII audit fields
        processed["redaction_status"] = "REDACTED" if is_redacted else (record.get("redaction_status") or "CLEAN")
        processed["redaction_categories"] = json.dumps(all_cats)
        processed["pii_processed_at"] = now_utc

        return processed

_minimizer = None

def get_pii_minimizer() -> PIIMinimizer:
    """Returns singleton instance of PIIMinimizer."""
    global _minimizer
    if _minimizer is None:
        _minimizer = PIIMinimizer()
    return _minimizer
