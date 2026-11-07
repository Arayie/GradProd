"""
LLM Client and Provider Abstraction
Supports Google Gemini, OpenAI-compatible APIs, local Ollama endpoints,
and a deterministic multilingual NLP engine for offline execution without API costs.
"""

from typing import Dict, Any, Optional, Tuple, List
import os
import time
import json
import logging
import re
import urllib.request
import urllib.error
import yaml

logger = logging.getLogger(__name__)

class LLMClient:
    """Configurable LLM client with provider governance, backoff, and offline fallback."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            config_path = os.path.join(base_dir, "config", "model_config.yml")

        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "active_provider": "auto",
                "providers": {
                    "rule_based_mock": {
                        "provider_name": "Deterministic NLP Engine",
                        "model_id": "rule-nlp-v2.0",
                        "temperature": 0.0,
                    }
                },
            }

        self.active_provider_setting = self.config.get("active_provider", "auto")
        self.provider_name, self.model_id, self.provider_type = self._resolve_active_provider()

    def _resolve_active_provider(self) -> Tuple[str, str, str]:
        """Resolve which inference provider to use based on configuration and environment variables."""
        forced = self.active_provider_setting

        if forced == "gemini" or (forced == "auto" and os.getenv("GEMINI_API_KEY")):
            if os.getenv("GEMINI_API_KEY"):
                cfg = self.config.get("providers", {}).get("gemini", {})
                return cfg.get("provider_name", "Google Gemini"), cfg.get("model_id", "gemini-1.5-flash"), "gemini"

        if forced == "openai" or (forced == "auto" and os.getenv("OPENAI_API_KEY")):
            if os.getenv("OPENAI_API_KEY"):
                cfg = self.config.get("providers", {}).get("openai", {})
                return cfg.get("provider_name", "OpenAI"), cfg.get("model_id", "gpt-4o-mini"), "openai"

        if forced == "ollama":
            cfg = self.config.get("providers", {}).get("ollama", {})
            return cfg.get("provider_name", "Local Ollama"), cfg.get("model_id", "llama3.2:latest"), "ollama"

        # Default fallback: deterministic rule-based NLP engine
        cfg = self.config.get("providers", {}).get("rule_based_mock", {})
        return (
            cfg.get("provider_name", "Deterministic NLP Engine"),
            cfg.get("model_id", "rule-nlp-v2.0"),
            "rule_based_mock",
        )

    def classify(
        self,
        system_prompt: str,
        user_prompt: str,
        evidence_id: str,
        review_text: str,
        app_name: str,
        star_rating: int,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Execute classification via active provider or deterministic fallback.
        Returns raw dictionary parsed from model JSON response.
        """
        start_time = time.time()

        if self.provider_type == "gemini":
            result = self._call_gemini(system_prompt, user_prompt)
        elif self.provider_type == "openai":
            result = self._call_openai(system_prompt, user_prompt)
        elif self.provider_type == "ollama":
            result = self._call_ollama(system_prompt, user_prompt)
        else:
            result = self._run_deterministic_nlp(
                evidence_id, review_text, app_name, star_rating, language
            )

        latency_ms = int((time.time() - start_time) * 1000)
        result["_metadata"] = {
            "model_provider": self.provider_name,
            "model_id": self.model_id,
            "latency_ms": latency_ms,
            "token_count_input": len(user_prompt) // 4,
            "token_count_output": len(json.dumps(result)) // 4,
        }

        return result

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Gemini API via REST endpoint with exponential backoff."""
        api_key = os.getenv("GEMINI_API_KEY")
        model = self.model_id
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
            except Exception as e:
                logger.warning(f"Gemini API attempt {attempt+1} failed: {e}")
                time.sleep(2**attempt)

        # If external API fails, gracefully fallback
        logger.error("Gemini API calls failed; falling back to deterministic NLP engine")
        return self._run_deterministic_nlp("unknown", user_prompt, "Groww", 3, "en")

    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call OpenAI or compatible API via REST endpoint."""
        api_key = os.getenv("OPENAI_API_KEY")
        url = "https://api.openai.com/v1/chat/completions"

        payload = {
            "model": self.model_id,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                return json.loads(text)
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}; falling back to deterministic engine")
            return self._run_deterministic_nlp("unknown", user_prompt, "Groww", 3, "en")

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call local Ollama endpoint."""
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model_id,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return json.loads(data["response"])
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}; falling back to deterministic engine")
            return self._run_deterministic_nlp("unknown", user_prompt, "Groww", 3, "en")

    def _run_deterministic_nlp(
        self,
        evidence_id: str,
        text: str,
        app_name: str,
        star_rating: int,
        language: str,
    ) -> Dict[str, Any]:
        """
        Deterministic, rule-guided multilingual NLP classification engine.
        Applies PRD lexicon patterns and extracts exact verbatim substrings.
        """
        lower = text.lower()
        spans: Dict[str, Optional[str]] = {}

        # 1. Relevance Screening
        sip_kw = ["sip", "systematic investment", "instalment", "installment", "autopay", "mandate", "nach", "monthly deduction"]
        mf_kw = ["mutual fund", "nav", "amc", "folio", "units", "elss", "redemption", "nifty", "index fund"]
        
        has_sip = any(k in lower for k in sip_kw) or any(k in lower for k in ["kisht", "har mahine", "auto debit"])
        has_mf = any(k in lower for k in mf_kw) or any(k in lower for k in ["paise lagaye", "invest", "investment"])

        if has_sip:
            relevance = "DIRECT_SIP_RELEVANT"
        elif has_mf:
            relevance = "GENERAL_INVESTMENT_RELEVANT"
        elif any(k in lower for k in ["stock", "demat", "trading", "intraday", "ipo", "share"]):
            relevance = "GENERAL_INVESTMENT_RELEVANT"
        elif any(k in lower for k in ["app", "ui", "login", "update", "slow", "bug", "support", "worst", "good"]):
            relevance = "GENERAL_APP_FEEDBACK"
        else:
            relevance = "IRRELEVANT"

        # 2. Lifecycle Stage Identification
        lifecycle_stage = "UNKNOWN"
        sec_lifecycle = []

        # Patterns for lifecycle stages with exact span extraction
        restart_pats = [r"(?:dobara|phir se|restart|resume)\s+.*?(?:sip|shuru)", r"restarted\s+my\s+sip", r"started\s+again"]
        stop_pats = [
            r"sip\s+band\b", r"cancel\s+(?:my\s+)?sip", r"stop\s+(?:my\s+)?sip",
            r"stopped\s+(?:my\s+)?sip", r"sip\s+cancel", r"mandate\s+cancel",
            r"redeemed\s+(?:my\s+)?funds", r"withdrawn\s+(?:all\s+)?money",
            r"no\s+way\s+to\s+stop", r"unable\s+to\s+cancel", r"cannot\s+cancel"
        ]
        pause_pats = [
            r"pause\s+sip", r"sip\s+pause", r"skip\s+(?:instalment|installment|sip)",
            r"skip\s+sip", r"modify\s+sip", r"change\s+sip\s+date", r"unable\s+to\s+pause",
            r"not\s+able\s+to\s+pause"
        ]
        expansion_pats = [r"step[\s\-]up", r"increase\s+sip", r"added\s+(?:another|new)\s+sip", r"top[\s\-]up"]
        setup_pats = [
            r"first\s+sip", r"first[\s\-]time", r"mandate\s+is\s+not\s+getting\s+approved",
            r"mandate\s+(?:reject|fail|pending|approval|error|stuck)", r"autopay\s+(?:setup|failed|register|reject)",
            r"bank\s+verification", r"penny\s+drop", r"kyc\s+(?:reject|pending|approval)",
            r"(?:mandate|autopay|nach)\s+.*?(?:fail|reject|pending|stuck|not\s+working)"
        ]
        early_pats = [
            r"first\s+(?:instalment|installment|payment|debit)", r"units\s+not\s+(?:allotted|allocated|credited)",
            r"money\s+deducted\s+but", r"paise\s+kat\s+gaye", r"amount\s+deducted\s+not\s+reflected",
            r"amount\s+debited\s+not", r"deducted\s+not\s+reflected"
        ]
        habit_pats = [
            r"every\s+month", r"monthly\s+sip", r"regularly\s+investing", r"for\s+(?:1|2|3|4|5|6)\s+years",
            r"har\s+mahine", r"continuously", r"investing\s+since"
        ]
        discovery_pats = [r"new\s+user", r"account\s+opening", r"just\s+started", r"onboarding", r"exploring"]

        def match_patterns(patterns: List[str]) -> Optional[str]:
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    return text[m.start():m.end()]
            return None

        # Friction patterns
        friction_pats = [
            r"customer\s+(?:support|care)", r"worst\s+(?:app|service|experience)",
            r"not\s+working", r"unable\s+to", r"cannot\s+", r"problem", r"bug\b",
            r"glitch", r"error", r"stuck", r"failed", r"cheat", r"fraud", r"pathetic",
            r"ticket", r"no\s+reply", r"no\s+response"
        ]

        # Check in logical lifecycle precedence
        restart_span = match_patterns(restart_pats)
        stop_span = match_patterns(stop_pats)
        pause_span = match_patterns(pause_pats)
        expansion_span = match_patterns(expansion_pats)
        setup_span = match_patterns(setup_pats)
        early_span = match_patterns(early_pats)
        habit_span = match_patterns(habit_pats)
        discovery_span = match_patterns(discovery_pats)
        friction_span = match_patterns(friction_pats)

        if restart_span:
            lifecycle_stage = "S7_RESTART"
            spans["S7_RESTART"] = restart_span
        elif stop_span:
            lifecycle_stage = "S6_PAUSE_STOP"
            spans["S6_PAUSE_STOP"] = stop_span
        elif pause_span:
            lifecycle_stage = "S5_FRICTION"
            spans["S5_FRICTION"] = pause_span
        elif expansion_span:
            lifecycle_stage = "S4_REVIEW"
            spans["S4_REVIEW"] = expansion_span
        elif setup_span:
            lifecycle_stage = "S1_SETUP"
            spans["S1_SETUP"] = setup_span
        elif early_span:
            lifecycle_stage = "S2_EARLY"
            spans["S2_EARLY"] = early_span
        elif habit_span:
            lifecycle_stage = "S3_HABIT"
            spans["S3_HABIT"] = habit_span
        elif discovery_span:
            lifecycle_stage = "S0_DISCOVERY"
            spans["S0_DISCOVERY"] = discovery_span
        elif friction_span and star_rating <= 2:
            lifecycle_stage = "S5_FRICTION"
            spans["S5_FRICTION"] = friction_span
        elif star_rating >= 4 and (has_sip or has_mf):
            lifecycle_stage = "S3_HABIT"
        elif relevance == "GENERAL_INVESTMENT_RELEVANT":
            lifecycle_stage = "GENERAL_INVESTMENT"

        # 3. Investor Intent
        intents = []
        if re.search(r"disciplin|habit|regular\s+saving|bachat\s+ki\s+aadat", lower):
            intents.append("DISCIPLINED_SAVING")
            m = re.search(r"(?:disciplin\w*|regular\s+saving|bachat\s+ki\s+aadat)", text, re.I)
            if m: spans["DISCIPLINED_SAVING"] = text[m.start():m.end()]
        if re.search(r"long\s*term|future|wealth|retirement|child|compounding|10\s+years", lower):
            intents.append("LONG_TERM_WEALTH_CREATION")
            m = re.search(r"(?:long\s*term|future|wealth|retirement|compounding)", text, re.I)
            if m: spans["LONG_TERM_WEALTH_CREATION"] = text[m.start():m.end()]
        if re.search(r"first\s*time|beginner|newbie|pehli\s*baar|first\s+sip", lower):
            intents.append("FIRST_TIME_INVESTING")
            m = re.search(r"(?:first\s*time|beginner|pehli\s*baar|first\s+sip)", text, re.I)
            if m: spans["FIRST_TIME_INVESTING"] = text[m.start():m.end()]
        if re.search(r"tax|80c|elss", lower):
            intents.append("TAX_PLANNING")
            m = re.search(r"(?:tax|80c|elss)", text, re.I)
            if m: spans["TAX_PLANNING"] = text[m.start():m.end()]
        if re.search(r"friend|colleague|brother|relative|dost\s+ne", lower):
            intents.append("PEER_INFLUENCE")
            m = re.search(r"(?:friend|colleague|brother|relative|dost\s+ne)", text, re.I)
            if m: spans["PEER_INFLUENCE"] = text[m.start():m.end()]
        if not intents:
            intents = ["UNKNOWN"]

        # 4. Expectations
        expectations = []
        if re.search(r"automatic|seamless|smooth|instant|hassle[\s\-]free", lower):
            expectations.append("EFFORTLESS_AUTOMATION")
        if re.search(r"safe|secure|trust|guarantee", lower):
            expectations.append("CAPITAL_SAFETY")
        if re.search(r"support|help|quick\s+response", lower):
            expectations.append("TIMELY_SUPPORT")
        if not expectations:
            expectations = ["NOT_STATED"]

        # 5. Investor Behaviour
        behaviours = []
        if setup_span: behaviours.append("ATTEMPTED_MANDATE_SETUP")
        if stop_span: behaviours.append("CANCELLED_SIP")
        if pause_span: behaviours.append("PAUSED_SIP")
        if re.search(r"support|ticket|mail|called|complaint", lower):
            behaviours.append("CONTACTED_SUPPORT")
            m = re.search(r"(?:support|ticket|mail|called|complaint)", text, re.I)
            if m: spans["CONTACTED_SUPPORT"] = text[m.start():m.end()]
        if re.search(r"nav|return|statement|portfolio", lower):
            behaviours.append("CHECKED_PAYMENT_STATUS")
        if not behaviours:
            behaviours = ["STARTED_SIP"] if has_sip else ["NOT_STATED"]

        # 6. Pain Points (Multi-label with granular extraction)
        pain_points = []

        # Mandate / Setup Failure
        m_mandate = re.search(r"(?:mandate\s+(?:is\s+not\s+getting\s+approved|fail\w*|reject\w*|pending|error|stuck|approval|never\s+execute)|nach\s+reject\w*|autopay\s+(?:fail\w*|reject\w*|pending|setup\s+fail)|bank\s+verification\s+fail|penny\s+drop|new\s+sip\s+activation\s+is\s+not\s+working)", text, re.I)
        if not m_mandate and any(k in lower for k in ["mandate", "autopay", "nach", "auto pay"]) and any(k in lower for k in ["fail", "reject", "pending", "stuck", "error", "problem", "issue", "not working", "in progress"]):
            m_mandate = re.search(r"(?:mandate|autopay|auto\s+pay|nach)", text, re.I)
        if m_mandate:
            pain_points.append("MANDATE_REGISTRATION_FAILURE")
            spans["MANDATE_REGISTRATION_FAILURE"] = text[m_mandate.start():m_mandate.end()]

        # Money deducted not reflected
        m_money = re.search(r"(?:money\s+deducted\s+(?:but|not|and\s+not)|amount\s+debited\s+not|paise\s+kat\s+gaye\s+lekin|paisa\s+reflect\s+nahi|amount\s+cut\s+but|units\s+not\s+(?:allotted|allocated|credited)|deducted\s+not\s+reflected)", text, re.I)
        if m_money:
            pain_points.append("MONEY_DEDUCTED_NOT_REFLECTED")
            spans["MONEY_DEDUCTED_NOT_REFLECTED"] = text[m_money.start():m_money.end()]

        # Double debit
        m_double = re.search(r"(?:double\s+debit|deducted\s+twice|two\s+times\s+debit|do\s+baar\s+cut)", text, re.I)
        if m_double:
            pain_points.append("DOUBLE_DEBIT")
            spans["DOUBLE_DEBIT"] = text[m_double.start():m_double.end()]

        # Autopay execution failure
        m_auto_fail = re.search(r"(?:autopay\s+fail\w*|kisht\s+miss|installment\s+miss|auto\s+debit\s+failed)", text, re.I)
        if m_auto_fail and "MANDATE_REGISTRATION_FAILURE" not in pain_points:
            pain_points.append("AUTOPAY_EXECUTION_FAILURE")
            spans["AUTOPAY_EXECUTION_FAILURE"] = text[m_auto_fail.start():m_auto_fail.end()]

        # NAV / Unit allotment delay or confusion
        m_nav = re.search(r"(?:nav\s+(?:samajh|delay|allot\w*|calculation)|zero\s+units)", text, re.I)
        if m_nav and "MONEY_DEDUCTED_NOT_REFLECTED" not in pain_points:
            pain_points.append("NAV_ALLOCATION_DELAY" if "allot" in m_nav.group().lower() or "unit" in m_nav.group().lower() else "NAV_CALCULATION_CONFUSION")
            spans[pain_points[-1]] = text[m_nav.start():m_nav.end()]

        # Negative returns / loss perception
        m_loss = re.search(r"(?:loss\s+mein|negative\s+return|loss\s+ho\s+raha|portfolio\s+in\s+red|losing\s+money|loss\s*&\s*gain|gain\s*&\s*loss|\blosses?\b)", text, re.I)
        if m_loss and (star_rating <= 2 or any(k in lower for k in ["return", "portfolio", "sip", "fund", "invest"])):
            pain_points.append("RETURN_REPORTING_DISCREPANCY")
            spans["RETURN_REPORTING_DISCREPANCY"] = text[m_loss.start():m_loss.end()]

        # SIP Pause / Cancellation difficulty
        m_cancel = re.search(r"(?:cannot\s+cancel|unable\s+to\s+cancel|cancel\s+sip|stop\s+sip|sip\s+band|unable\s+to\s+stop|cannot\s+stop|no\s+way\s+to\s+stop)", text, re.I)
        m_pause = re.search(r"(?:pause\s+sip|sip\s+pause|skip\s+sip|unable\s+to\s+pause|cannot\s+pause|skip\s+(?:instalment|installment)|modify\s+sip)", text, re.I)
        if m_cancel:
            pain_points.append("SIP_CANCELLATION_DIFFICULTY")
            spans["SIP_CANCELLATION_DIFFICULTY"] = text[m_cancel.start():m_cancel.end()]
        elif m_pause:
            pain_points.append("SIP_PAUSE_DIFFICULTY")
            spans["SIP_PAUSE_DIFFICULTY"] = text[m_pause.start():m_pause.end()]

        # Unresponsive customer support
        m_supp = re.search(r"(?:customer\s*(?:support|care)|support\s+team|helpdesk|bot\s+loop|no\s+response|worst\s+support|ticket|no\s+reply)", text, re.I)
        if m_supp and (star_rating <= 2 or "not" in lower or "worst" in lower or "useless" in lower):
            pain_points.append("CUSTOMER_SUPPORT_UNRESPONSIVE")
            spans["CUSTOMER_SUPPORT_UNRESPONSIVE"] = text[m_supp.start():m_supp.end()]

        # If 4 or 5 stars and no pain points detected
        if not pain_points:
            if star_rating >= 4 or any(k in lower for k in ["good", "great", "excellent", "best", "smooth", "love"]):
                pain_points = ["NO_PAIN_POINT_STATED"]
            elif star_rating <= 2:
                pain_points = ["UNRESOLVED_COMPLAINT"]
            else:
                pain_points = ["NO_PAIN_POINT_STATED"]

        # Harmonize lifecycle stage with detected pain point
        if "MANDATE_REGISTRATION_FAILURE" in pain_points:
            lifecycle_stage = "S1_SETUP"
        elif "MONEY_DEDUCTED_NOT_REFLECTED" in pain_points:
            lifecycle_stage = "S2_EARLY"
        elif "SIP_CANCELLATION_DIFFICULTY" in pain_points:
            lifecycle_stage = "S6_PAUSE_STOP"
        elif "SIP_PAUSE_DIFFICULTY" in pain_points or "CUSTOMER_SUPPORT_UNRESPONSIVE" in pain_points:
            lifecycle_stage = "S5_FRICTION"
        elif "RETURN_REPORTING_DISCREPANCY" in pain_points:
            lifecycle_stage = "S3_HABIT"
        elif "UNRESOLVED_COMPLAINT" in pain_points:
            lifecycle_stage = "S5_FRICTION"
        elif "NO_PAIN_POINT_STATED" in pain_points and lifecycle_stage in ("UNKNOWN", "GENERAL_INVESTMENT"):
            lifecycle_stage = "S3_HABIT"

        # 7. Triggers
        triggers = []
        if "MANDATE_REGISTRATION_FAILURE" in pain_points: triggers.append("MANDATE_FAILURE")
        if "AUTOPAY_EXECUTION_FAILURE" in pain_points or "MONEY_DEDUCTED_NOT_REFLECTED" in pain_points: triggers.append("PAYMENT_FAILURE")
        if "RETURN_REPORTING_DISCREPANCY" in pain_points: triggers.append("NEGATIVE_RETURN_PERCEPTION")
        if "CUSTOMER_SUPPORT_UNRESPONSIVE" in pain_points: triggers.append("UNHELPFUL_SUPPORT_RESPONSE")
        if not triggers:
            triggers = ["NOT_STATED"]

        # 8. Outside-App Workarounds
        outside_actions = []
        if re.search(r"bank\s+(?:statement|branch|manager|account)", lower): outside_actions.append("CHECKED_BANK_STATEMENT")
        if re.search(r"youtube|video|tutorial", lower): outside_actions.append("WATCHED_YOUTUBE_OR_TUTORIAL")
        if re.search(r"twitter|x\.com|social\s+media|consumer\s+court", lower): outside_actions.append("COMPLAINED_ON_SOCIAL_MEDIA")
        if "CONTACTED_SUPPORT" in behaviours: outside_actions.append("CONTACTED_CUSTOMER_SUPPORT")
        if not outside_actions:
            outside_actions = ["NOT_STATED"]

        # 9. Reported Outcome
        if "S6_PAUSE_STOP" in [lifecycle_stage] or "CANCELLED_SIP" in behaviours:
            outcome = "STOPPED_SIP"
        elif "S5_FRICTION" in [lifecycle_stage] or "PAUSED_SIP" in behaviours:
            outcome = "PAUSED_SIP"
        elif any(p in pain_points for p in ["MANDATE_REGISTRATION_FAILURE", "MONEY_DEDUCTED_NOT_REFLECTED", "CUSTOMER_SUPPORT_UNRESPONSIVE"]):
            outcome = "UNRESOLVED"
        elif star_rating >= 4:
            outcome = "SATISFIED"
        elif "S3_HABIT" == lifecycle_stage:
            outcome = "CONTINUED_SIP"
        else:
            outcome = "NOT_STATED"

        # 10. Disclosed Demographics (Strict privacy default UNKNOWN)
        disclosed_context = {
            "age_band": "UNKNOWN",
            "investment_experience": "FIRST_TIME" if "FIRST_TIME_INVESTING" in intents else "UNKNOWN",
            "income_stability": "UNKNOWN",
        }

        # Explicit age disclosure check (e.g. "I am 22 years old", "20 year old student")
        m_age = re.search(r"\b(?:i\s+am\s+a?\s*)?(\d{2})\s*(?:year|yr)s?\s*old\b", lower)
        if m_age:
            age = int(m_age.group(1))
            if age < 25: disclosed_context["age_band"] = "STUDENT_COLLEGE"
            elif age < 35: disclosed_context["age_band"] = "YOUNG_PROFESSIONAL"
            elif age < 60: disclosed_context["age_band"] = "MID_CAREER"
            else: disclosed_context["age_band"] = "RETIREE_SENIOR"

        # 11. Confidence Scores
        base_conf = 0.92 if spans else 0.75
        if language in ("hi", "hi-Latn", "mixed"):
            base_conf = 0.88 if spans else 0.72

        confidence_scores = {
            "overall": round(base_conf, 3),
            "lifecycle_stage": round(0.95 if lifecycle_stage != "UNKNOWN" else 0.60, 3),
            "investor_intent": round(0.85 if intents != ["UNKNOWN"] else 0.65, 3),
            "pain_points": round(0.95 if pain_points != ["NO_PAIN_POINT_STATED"] else 0.85, 3),
            "reported_outcome": round(0.88 if outcome != "NOT_STATED" else 0.65, 3),
        }

        return {
            "evidence_id": evidence_id,
            "primary_research_relevance": relevance,
            "lifecycle_stage": lifecycle_stage,
            "secondary_lifecycle_stages": sec_lifecycle,
            "investor_intent": intents,
            "expectations": expectations,
            "behaviour": behaviours,
            "pain_points": pain_points,
            "triggers": triggers,
            "outside_app_actions": outside_actions,
            "reported_outcome": outcome,
            "disclosed_context": disclosed_context,
            "confidence_scores": confidence_scores,
            "evidence_spans": spans,
            "reasoning_summary": f"Classified review for {app_name} with rating {star_rating}. Primary pain points: {', '.join(pain_points)}.",
        }
