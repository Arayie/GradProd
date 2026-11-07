"""
Multilingual Language and Script Detection for Growww Discovery Engine.
Implements Task 2: detects English, Hindi (Devanagari), Hinglish (Romanized Hindi),
Code-Switching, and other Indian languages while preserving financial terms (SIP, NAV, KYC, UPI).
"""
import re
import unicodedata
from typing import Dict, Any, Tuple, Set

# Script Unicode Ranges
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
KANNADA_RE = re.compile(r"[\u0C80-\u0CFF]")
MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")
GUJARATI_RE = re.compile(r"[\u0A80-\u0AFF]")

# Domain Financial and App terms that should NOT bias toward English
DOMAIN_NEUTRAL_TOKENS: Set[str] = {
    "sip", "nav", "kyc", "upi", "nach", "mandate", "autopay", "demat",
    "ipo", "otp", "mf", "amc", "bse", "nse", "sebi", "cams", "kfintech",
    "groww", "zerodha", "coin", "kite", "upstox", "angel", "angelone",
    "indmoney", "etmoney", "paytm", "app", "fund", "funds", "mutual",
    "stocks", "stock", "portfolio", "account", "bank", "payment",
    "login", "update", "update", "server", "system", "email", "support"
}

# Common Romanized Hindi (Hinglish) Vocabulary (Function words, pronouns, verbs, fintech nouns)
HINGLISH_VOCABULARY: Set[str] = {
    # Pronouns & interrogatives
    "mera", "meri", "mere", "mujhe", "mujhko", "hum", "humne", "hamara",
    "hamare", "hamari", "apna", "apne", "apni", "kya", "kyu", "kyun",
    "kaise", "kaha", "kab", "kitna", "kitne", "kitni", "kaun", "kise",
    # Negation & assertion
    "nahi", "nhi", "nahin", "na", "mat", "haan", "han", "bilkul",
    # Auxiliary verbs & states
    "hai", "hain", "ho", "hoga", "hogi", "hoge", "hote", "hoti", "hota",
    "tha", "thi", "the", "raha", "rahi", "rahe", "gaya", "gayi", "gaye",
    "hua", "hui", "hue", "aaya", "aayi", "aaye", "aata", "aati",
    # Connectives & prepositions
    "par", "pe", "mein", "me", "se", "ko", "ka", "ki", "ke", "lekin",
    "magar", "aur", "bhi", "toh", "to", "ab", "jab", "tab", "wala", "wali", "wale",
    # Common actions & verbs
    "karna", "karo", "kare", "karein", "kiya", "kar", "diya", "liya",
    "dedo", "ledo", "de", "do", "bolo", "batao", "bataye", "samjhao",
    "rokna", "rok", "band", "chahiye", "samajh", "nuksan", "fayda",
    "kisht", "nivesh", "shuru", "dikha", "dikkat", "wapas", "paise",
    "paisa", "rupaye", "rupay", "kat", "kate", "katna", "nikalna",
    "nikala", "nikalo", "jama", "aata", "daala", "dala", "rakha",
    # Slang, expressions & emotional markers
    "bhai", "yaar", "sir", "faltu", "bakwas", "bekar", "achha", "accha",
    "bura", "chor", "dhokha", "loot", "lutera", "sahi", "galat", "khatam",
    "madad", "pareshaan", "pareshani", "barbaad", "kripya", "dhanyawad"
}

# Common English stopwords for contrast
ENGLISH_STOPWORDS: Set[str] = {
    "the", "and", "is", "in", "to", "of", "it", "this", "that", "with",
    "for", "on", "was", "as", "are", "by", "from", "at", "not", "be",
    "have", "has", "had", "they", "you", "my", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "very", "great", "worst", "best"
}

class LanguageDetector:
    """Deterministic, zero-dependency multilingual script and language detector for Indian reviews."""

    def __init__(self):
        self.method_name = "heuristic_lexical_script_v1"

    def detect_script(self, text: str) -> str:
        """
        Identifies the dominant script used in the text.
        Returns: 'DEVANAGARI', 'OTHER_INDIC', 'LATIN', 'MIXED', or 'UNKNOWN'.
        """
        if not text:
            return "UNKNOWN"

        has_devanagari = bool(DEVANAGARI_RE.search(text))
        has_other_indic = bool(
            TAMIL_RE.search(text) or TELUGU_RE.search(text) or
            BENGALI_RE.search(text) or KANNADA_RE.search(text) or
            MALAYALAM_RE.search(text) or GUJARATI_RE.search(text)
        )
        has_latin = bool(re.search(r"[a-zA-Z]", text))

        if has_other_indic:
            return "OTHER_INDIC"
        if has_devanagari and has_latin:
            # Check if Latin is just domain tokens or substantial
            latin_words = re.findall(r"[a-zA-Z]{3,}", text.lower())
            non_domain_latin = [w for w in latin_words if w not in DOMAIN_NEUTRAL_TOKENS]
            if len(non_domain_latin) >= 3:
                return "MIXED"
            return "DEVANAGARI"
        if has_devanagari:
            return "DEVANAGARI"
        if has_latin:
            return "LATIN"
        return "UNKNOWN"

    def detect_language(self, text: str) -> Tuple[str, float, str, str]:
        """
        Determines language, confidence, script, and detection method.
        Returns: (language_detected, confidence, script_detected, method)
        Languages:
          - 'en': English
          - 'hi': Hindi (Devanagari)
          - 'hi-Latn': Hinglish / Romanized Hindi
          - 'mixed': Code-switching (English + Hindi/Hinglish)
          - 'other': Other Indian language (Tamil, Telugu, etc.)
          - 'unknown': Ambiguous or empty
        """
        if not text or not text.strip():
            return "unknown", 0.0, "UNKNOWN", self.method_name

        script = self.detect_script(text)

        # 1. Other Indic scripts
        if script == "OTHER_INDIC":
            return "other", 0.90, script, self.method_name

        # 2. Devanagari Hindi
        if script == "DEVANAGARI":
            return "hi", 0.95, script, self.method_name

        # 3. Mixed Devanagari + Latin Script (Explicit Code-Switching)
        if script == "MIXED":
            return "mixed", 0.90, script, self.method_name

        # 4. Latin Script: Differentiate English vs Hinglish (hi-Latn) vs Code-Switching
        # Tokenize lowercase alphabetic tokens
        tokens = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
        if not tokens:
            return "unknown", 0.20, script, self.method_name

        # Filter out neutral domain tokens
        eval_tokens = [t for t in tokens if t not in DOMAIN_NEUTRAL_TOKENS]
        if not eval_tokens:
            # Text consisted entirely of domain words e.g. "SIP App"
            return "en", 0.60, script, self.method_name

        total_eval = len(eval_tokens)
        hinglish_matches = [t for t in eval_tokens if t in HINGLISH_VOCABULARY]
        english_matches = [t for t in eval_tokens if t in ENGLISH_STOPWORDS]

        num_hinglish = len(hinglish_matches)
        num_english = len(english_matches)

        hinglish_ratio = num_hinglish / total_eval
        english_ratio = num_english / total_eval

        # Distinct Hinglish vocabulary words
        distinct_hinglish = len(set(hinglish_matches))

        # Decision rules
        # Pure/Dominant Hinglish:
        if distinct_hinglish >= 3 or (num_hinglish >= 2 and hinglish_ratio >= 0.20):
            # Check for substantial English grammatical presence
            if num_english >= 4 and english_ratio >= 0.25:
                # Both languages have strong presence -> Code switching
                return "mixed", 0.85, "LATIN", self.method_name
            confidence = min(0.98, 0.70 + (distinct_hinglish * 0.05) + (hinglish_ratio * 0.20))
            return "hi-Latn", round(confidence, 2), "LATIN", self.method_name

        # Single Hinglish token in a longer sentence
        if num_hinglish >= 1 and distinct_hinglish >= 1 and total_eval <= 6:
            # Short phrase like "Paise kat gaye", "SIP rokna hai"
            return "hi-Latn", 0.85, "LATIN", self.method_name

        # High English presence
        if num_english >= 2 or english_ratio >= 0.15:
            confidence = min(0.95, 0.75 + (english_ratio * 0.20))
            return "en", round(confidence, 2), "LATIN", self.method_name

        # Short text fallback: check if words look English
        # If words are common English words
        if all(len(t) >= 2 for t in eval_tokens):
            return "en", 0.70, "LATIN", self.method_name

        return "unknown", 0.40, "LATIN", self.method_name

    def enrich_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches normalized review record with multilingual detection fields."""
        text = record.get("review_text") or record.get("review_text_original") or ""
        lang, conf, script, method = self.detect_language(text)

        enriched = dict(record)
        enriched["language_detected"] = lang
        enriched["language_confidence"] = conf
        enriched["script_detected"] = script
        enriched["language_detection_method"] = method
        return enriched

_detector = None

def get_language_detector() -> LanguageDetector:
    """Returns singleton instance of LanguageDetector."""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector
