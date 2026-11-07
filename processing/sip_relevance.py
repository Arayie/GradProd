"""
SIP Relevance and Discovery Query Screener for Growww Discovery Engine.
Implements Task 3 and Task 4: deterministic keyword and phrase screening across
Categories A-H, 15 boolean research coverage flags, and relevance status assignment.
"""
import os
import sys
import re
import json
import yaml
from typing import Dict, Any, List, Set, Tuple, Optional

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "review_queries.yml"
)

class SIPRelevanceClassifier:
    """Classifies customer reviews into SIP relevance categories using deterministic phrase matching."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.version = "1.0.0"
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.general_investment_terms: List[str] = []
        self.general_app_terms: List[str] = []
        self._compiled_category_patterns: Dict[str, List[re.Pattern]] = {}
        self._load_config()

    def _load_config(self):
        """Loads and compiles query patterns from review_queries.yml."""
        if not os.path.exists(self.config_path):
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        self.version = cfg.get("version", "1.0.0")
        self.categories = cfg.get("categories", {})
        self.general_investment_terms = cfg.get("general_investment_terms", [])
        self.general_app_terms = cfg.get("general_app_terms", [])

        # Compile category regex patterns
        for cat_name, cat_data in self.categories.items():
            patterns = []
            all_raw = (
                cat_data.get("patterns_en", []) +
                cat_data.get("patterns_hi", []) +
                cat_data.get("patterns_hinglish", [])
            )
            for phrase in all_raw:
                p_clean = phrase.strip().lower()
                if not p_clean:
                    continue
                # Use word boundary where reasonable
                escaped = re.escape(p_clean)
                patterns.append(re.compile(rf"\b{escaped}\b", re.IGNORECASE))
            self._compiled_category_patterns[cat_name] = patterns

    # Pre-compiled regexes for the 15 boolean coverage flags
    FLAG_REGEXES = {
        "mentions_sip": re.compile(r"\b(sip|sips|systematic\s+investment)\b", re.IGNORECASE),
        "mentions_mutual_fund": re.compile(r"\b(mutual\s*funds?|mf|index\s+funds?|debt\s+funds?|elss|amc|etf|equity\s+funds?)\b", re.IGNORECASE),
        "mentions_payment": re.compile(r"\b(payments?|paid|debits?|deducted?|deductions?|paise|paisa|rupaye|amount|balance|failed\s+payment)\b", re.IGNORECASE),
        "mentions_mandate": re.compile(r"\b(mandates?|nach|e-?mandates?|e-?nach|bank\s+mandate)\b", re.IGNORECASE),
        "mentions_autopay": re.compile(r"\b(autopay|auto-?pay|auto-?debit|standing\s+instruction)\b", re.IGNORECASE),
        "mentions_instalment": re.compile(r"\b(instalments?|installments?|kisht|kist|monthly\s+due)\b", re.IGNORECASE),
        "mentions_nav": re.compile(r"\b(nav|net\s+asset\s+value|allotment\s+nav|cut-?off)\b", re.IGNORECASE),
        "mentions_returns": re.compile(r"\b(returns?|xirr|cagr|profits?|loss|losses|yield|nuksan|fayda)\b", re.IGNORECASE),
        "mentions_units": re.compile(r"\b(units?|unit\s+allotment|allotted|allotting)\b", re.IGNORECASE),
        "mentions_pause_stop": re.compile(r"\b(pause|paused|pausing|stop|stopped|stopping|cancels?|cancelled|canceling|discontinue|discontinued|band\s+kar|rokna|rok)\b", re.IGNORECASE),
        "mentions_restart": re.compile(r"\b(restarts?|restarted|restarting|resumes?|resumed|resuming|re-?activate|shuru\s+kar|dobara)\b", re.IGNORECASE),
        "mentions_redemption": re.compile(r"\b(redeem|redeems?|redeemed|redemption|withdraw|withdraws?|withdrawal|withdrawing|exit\s+load|nikalna|payout)\b", re.IGNORECASE),
        "mentions_support": re.compile(r"\b(customer\s+support|customer\s+care|support|helpdesk|tickets?|agents?|email|call|toll-?free|complaints?)\b", re.IGNORECASE),
        "mentions_kyc": re.compile(r"\b(kyc|ckyc|pan|aadhaar|verification|documents?|onboarding)\b", re.IGNORECASE),
        "mentions_trust": re.compile(r"\b(trust|scams?|frauds?|cheats?|cheated|chor|dhokha|loot|fake|stolen|unreliable|worst)\b", re.IGNORECASE),
    }

    def evaluate_coverage_flags(self, text: str) -> Dict[str, int]:
        """Evaluates 15 preliminary boolean research coverage flags against review text."""
        flags = {}
        for flag_name, pattern in self.FLAG_REGEXES.items():
            flags[flag_name] = 1 if bool(pattern.search(text)) else 0
        return flags

    def match_categories(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Matches text against categories A through H.
        Returns: (matched_category_names, matched_terms)
        """
        matched_cats = []
        matched_terms = []

        for cat_name, patterns in self._compiled_category_patterns.items():
            cat_matched = False
            for pat in patterns:
                match = pat.search(text)
                if match:
                    cat_matched = True
                    matched_terms.append(match.group(0).lower())
            if cat_matched:
                matched_cats.append(cat_name)

        return matched_cats, list(set(matched_terms))

    def classify_review(self, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs full SIP relevance screening on review text and title.
        Returns relevance status, matched categories, matched terms, and 15 boolean flags.
        """
        combined_text = f"{title or ''} {text or ''}".strip()
        if not combined_text:
            return {
                "sip_relevance_status": "IRRELEVANT",
                "matched_query_categories": "[]",
                "matched_terms": "[]",
                "relevance_rule_version": self.version,
                **{k: 0 for k in self.FLAG_REGEXES}
            }

        # 1. Evaluate 15 Boolean flags
        flags = self.evaluate_coverage_flags(combined_text)

        # 2. Match Categories A-H
        matched_cats, matched_terms = self.match_categories(combined_text)

        # 3. Determine Relevance Status
        # Rules:
        # A. DIRECT_SIP_RELEVANT:
        #    - Mentions SIP explicitly AND has any SIP journey category or related term,
        #    - OR mentions SIP + setup/payment/instalment/pause/stop/units/returns.
        # B. INDIRECT_SIP_RELEVANT:
        #    - Does NOT explicitly mention SIP, but mentions mandate, autopay, or recurring instalment payment failure.
        # C. GENERAL_INVESTMENT_RELEVANT:
        #    - Mentions mutual funds, NAV, returns, redemption, portfolio, demat without SIP-specific context.
        # D. GENERAL_APP_FEEDBACK:
        #    - Mentions general app terms (UI, update, crash, bug) without investment terms.
        # E. IRRELEVANT:
        #    - Short generic reviews ("good", "ok", "nice app") or unrelated comments.

        has_explicit_sip = bool(flags["mentions_sip"])
        has_mandate_or_autopay = bool(flags["mentions_mandate"] or flags["mentions_autopay"] or flags["mentions_instalment"])
        has_general_investment = bool(flags["mentions_mutual_fund"] or flags["mentions_nav"] or flags["mentions_returns"] or flags["mentions_redemption"])

        status = "IRRELEVANT"

        if has_explicit_sip:
            # Check if it has any category or substance
            if matched_cats or has_mandate_or_autopay or flags["mentions_payment"] or flags["mentions_pause_stop"] or flags["mentions_restart"]:
                status = "DIRECT_SIP_RELEVANT"
            else:
                # E.g. "SIP app is good" -> still direct SIP relevant keyword
                status = "DIRECT_SIP_RELEVANT"

        elif has_mandate_or_autopay and (flags["mentions_payment"] or "payment_and_mandate_failures" in matched_cats or "sip_setup_and_onboarding" in matched_cats):
            status = "INDIRECT_SIP_RELEVANT"

        elif has_general_investment:
            status = "GENERAL_INVESTMENT_RELEVANT"

        else:
            # Check for general app feedback
            app_pattern = re.compile(r"\b(ui|interface|update|crash|crashing|slow|bug|glitch|login|logout|dark\s+mode|fingerprint|face\s+id|battery|ads?|rating|fix|issue|working)\b", re.IGNORECASE)
            if app_pattern.search(combined_text):
                status = "GENERAL_APP_FEEDBACK"
            else:
                # E.g. "Good", "Bad", "ok" -> Irrelevant to investment research
                status = "IRRELEVANT"

        return {
            "sip_relevance_status": status,
            "matched_query_categories": json.dumps(matched_cats),
            "matched_terms": json.dumps(matched_terms),
            "relevance_rule_version": self.version,
            **flags
        }

    def enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches normalized review record with SIP relevance and coverage fields."""
        text = record.get("review_text") or record.get("review_text_original") or ""
        title = record.get("review_title")

        classification = self.classify_review(text=text, title=title)
        enriched = dict(record)
        enriched.update(classification)
        return enriched

_classifier = None

def get_sip_classifier() -> SIPRelevanceClassifier:
    """Returns singleton instance of SIPRelevanceClassifier."""
    global _classifier
    if _classifier is None:
        _classifier = SIPRelevanceClassifier()
    return _classifier
