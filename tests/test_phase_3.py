"""
Comprehensive Automated Unit and Integration Test Suite for Phase 3:
Standardization, Language Detection, PII Minimization, SIP Relevance,
Deduplication, Retention, Quality Scoring, and End-to-End Pipeline.
"""
import unittest
from datetime import datetime, timedelta

from processing.normalize import ReviewNormalizer
from processing.language_detection import LanguageDetector
from processing.pii_minimization import PIIMinimizer
from processing.sip_relevance import SIPRelevanceClassifier
from processing.deduplicate import AdvancedDeduplicator
from processing.retention import RetentionManager
from processing.data_quality import DataQualityScorer
from processing.pipeline import ProcessingPipeline

class TestPhase3Normalization(unittest.TestCase):
    """Tests Task 1: Canonical data normalization and standardization."""

    def setUp(self):
        self.normalizer = ReviewNormalizer()

    def test_whitespace_and_html_cleaning(self):
        text = "<p>My &amp; your   SIP   failed &#39;today&#39;!\n\n\n\nNot working.</p>"
        cleaned, is_empty = self.normalizer.clean_text(text)
        self.assertFalse(is_empty)
        self.assertEqual(cleaned, "My & your SIP failed 'today'!\n\nNot working.")

    def test_unicode_normalization(self):
        text = "Groww\u00A0App\u200B"  # Non-breaking space and zero-width space
        cleaned, _ = self.normalizer.clean_text(text)
        self.assertEqual(cleaned, "Groww App")

    def test_date_utc_standardization(self):
        iso_str = "2026-11-04T06:49:50-07:00"
        utc_res = self.normalizer.parse_utc_timestamp(iso_str)
        self.assertEqual(utc_res, "2026-11-04 13:49:50")

    def test_rating_validation(self):
        val, is_valid = self.normalizer.validate_rating("5")
        self.assertEqual(val, 5)
        self.assertTrue(is_valid)

        # Clamping invalid rating
        val_bad, is_valid_bad = self.normalizer.validate_rating("7")
        self.assertEqual(val_bad, 5)
        self.assertFalse(is_valid_bad)

    def test_original_text_preserved(self):
        raw = {
            "app_id": "groww",
            "store": "Apple",
            "review_text": "<b>Great</b>  app for SIP!",
            "star_rating": 5,
            "review_created_at": "2026-11-04T10:00:00Z"
        }
        res = self.normalizer.normalize_record(raw)
        self.assertEqual(res["review_text_original"], "<b>Great</b>  app for SIP!")
        self.assertEqual(res["review_text"], "Great app for SIP!")
        self.assertEqual(res["store"], "apple_app_store")
        self.assertEqual(res["app_name"], "Groww Stocks, Mutual Fund, IPO")

class TestPhase3LanguageDetection(unittest.TestCase):
    """Tests Task 2: Multilingual language and script detection."""

    def setUp(self):
        self.detector = LanguageDetector()

    def test_english_review(self):
        lang, conf, script, _ = self.detector.detect_language("My SIP payment failed three times on Groww app.")
        self.assertEqual(lang, "en")
        self.assertEqual(script, "LATIN")
        self.assertGreaterEqual(conf, 0.70)

    def test_devanagari_hindi_review(self):
        lang, conf, script, _ = self.detector.detect_language("मेरी पहली एसआईपी शुरू नहीं हो रही है।")
        self.assertEqual(lang, "hi")
        self.assertEqual(script, "DEVANAGARI")
        self.assertGreaterEqual(conf, 0.90)

    def test_hinglish_review(self):
        lang, conf, script, _ = self.detector.detect_language("Mera SIP ka payment nahi hua aur paise kat gaye.")
        self.assertEqual(lang, "hi-Latn")
        self.assertEqual(script, "LATIN")
        self.assertGreaterEqual(conf, 0.85)

    def test_financial_term_preservation(self):
        # Domain terms like SIP, NAV, UPI, Mandate should not force Hindi text to English
        lang, conf, _, _ = self.detector.detect_language("Mandate activate nahi ho raha, paise kat gaye.")
        self.assertEqual(lang, "hi-Latn")

    def test_code_switching(self):
        lang, _, script, _ = self.detector.detect_language(
            "My monthly mutual fund order is in pending state because bank account se paise kat gaye"
        )
        self.assertEqual(lang, "mixed")

class TestPhase3SIPRelevance(unittest.TestCase):
    """Tests Task 3 and Task 4: SIP relevance screening and 15 boolean flags."""

    def setUp(self):
        self.classifier = SIPRelevanceClassifier()

    def test_direct_sip_failure(self):
        res = self.classifier.classify_review(
            text="My SIP payment failed and monthly instalment was deducted without confirmation.",
            title="SIP Failure"
        )
        self.assertEqual(res["sip_relevance_status"], "DIRECT_SIP_RELEVANT")
        self.assertEqual(res["mentions_sip"], 1)
        self.assertEqual(res["mentions_payment"], 1)
        self.assertEqual(res["mentions_instalment"], 1)

    def test_indirect_mandate_failure(self):
        res = self.classifier.classify_review(
            text="Auto debit mandate failed on my bank account for recurring mutual fund order.",
            title="Autopay Error"
        )
        self.assertEqual(res["sip_relevance_status"], "INDIRECT_SIP_RELEVANT")
        self.assertEqual(res["mentions_sip"], 0)
        self.assertEqual(res["mentions_mandate"], 1)
        self.assertEqual(res["mentions_autopay"], 1)

    def test_general_investment_review(self):
        res = self.classifier.classify_review(
            text="Mutual fund portfolio value is down. NAV calculation seems delayed by one day.",
            title="Portfolio Returns"
        )
        self.assertEqual(res["sip_relevance_status"], "GENERAL_INVESTMENT_RELEVANT")
        self.assertEqual(res["mentions_sip"], 0)
        self.assertEqual(res["mentions_mutual_fund"], 1)
        self.assertEqual(res["mentions_nav"], 1)
        self.assertEqual(res["mentions_returns"], 1)

    def test_general_app_feedback(self):
        res = self.classifier.classify_review(
            text="App is crashing after latest update. Fingerprint login is not working.",
            title="Buggy Update"
        )
        self.assertEqual(res["sip_relevance_status"], "GENERAL_APP_FEEDBACK")
        self.assertEqual(res["mentions_sip"], 0)

    def test_irrelevant_review(self):
        res = self.classifier.classify_review(text="Superb app, thanks.", title="Nice")
        self.assertEqual(res["sip_relevance_status"], "IRRELEVANT")

    def test_positive_sip_review_not_pain_point(self):
        res = self.classifier.classify_review(
            text="Starting my first SIP was super easy and fast. Loved the experience!",
            title="Great First SIP"
        )
        self.assertEqual(res["sip_relevance_status"], "DIRECT_SIP_RELEVANT")
        self.assertEqual(res["mentions_sip"], 1)
        self.assertIn("sip_first_start_and_discovery", res["matched_query_categories"])

class TestPhase3PIIMinimization(unittest.TestCase):
    """Tests Task 5: PII detection and redaction."""

    def setUp(self):
        self.minimizer = PIIMinimizer()

    def test_phone_and_email_redaction(self):
        text = "Contact me at 9876543210 or investor.help@gmail.com for refund."
        redacted, cats = self.minimizer.redact_text(text)
        self.assertIn("[PHONE_REDACTED]", redacted)
        self.assertIn("[EMAIL_REDACTED]", redacted)
        self.assertNotIn("9876543210", redacted)
        self.assertNotIn("investor.help@gmail.com", redacted)
        self.assertEqual(cats, ["email", "phone"])

    def test_pan_and_upi_redaction(self):
        text = "My PAN is ABCDE1234F and UPI ID is testuser@oksbi."
        redacted, cats = self.minimizer.redact_text(text)
        self.assertIn("[PAN_REDACTED]", redacted)
        self.assertIn("[UPI_REDACTED]", redacted)
        self.assertNotIn("ABCDE1234F", redacted)
        self.assertNotIn("testuser@oksbi", redacted)
        self.assertEqual(cats, ["pan", "upi"])

    def test_clean_review_remains_clean(self):
        text = "Smooth mutual fund SIP investment experience."
        redacted, cats = self.minimizer.redact_text(text)
        self.assertEqual(redacted, text)
        self.assertEqual(cats, [])

class TestPhase3Deduplication(unittest.TestCase):
    """Tests Task 6: Multi-tier deduplication and near-duplicate clustering."""

    def setUp(self):
        self.dedup = AdvancedDeduplicator()

    def test_source_id_duplicate(self):
        r1 = {"evidence_id": "EV1", "app_id": "groww", "store": "apple_app_store", "source_record_id": "SR1", "review_text": "Text 1"}
        r2 = {"evidence_id": "EV2", "app_id": "groww", "store": "apple_app_store", "source_record_id": "SR1", "review_text": "Text 2"}
        res1 = self.dedup.evaluate_record(r1)
        res2 = self.dedup.evaluate_record(r2)
        self.assertEqual(res1["duplicate_status"], "UNIQUE")
        self.assertEqual(res2["duplicate_status"], "DUPLICATE_SOURCE_ID")
        self.assertEqual(res2["duplicate_of_evidence_id"], "EV1")

    def test_content_hash_duplicate(self):
        r1 = {"evidence_id": "EV1", "app_id": "groww", "store": "apple_app_store", "source_record_id": "SR1", "review_text": "Exact same review text."}
        r2 = {"evidence_id": "EV2", "app_id": "groww", "store": "apple_app_store", "source_record_id": "SR2", "review_text": "Exact same review text."}
        self.dedup.evaluate_record(r1)
        res2 = self.dedup.evaluate_record(r2)
        self.assertEqual(res2["duplicate_status"], "DUPLICATE_HASH")
        self.assertEqual(res2["duplicate_of_evidence_id"], "EV1")

    def test_near_duplicate_candidate_clustering(self):
        t1 = "My SIP payment failed on HDFC bank autopay multiple times today without any explanation from Groww."
        t2 = "My SIP payment failed on HDFC bank autopay multiple times today without any explanation from Groww team."
        r1 = {"evidence_id": "EV1", "app_id": "groww", "store": "apple_app_store", "source_record_id": "SR1", "review_text": t1}
        r2 = {"evidence_id": "EV2", "app_id": "groww", "store": "apple_app_store", "source_record_id": "SR2", "review_text": t2}
        self.dedup.evaluate_record(r1)
        res2 = self.dedup.evaluate_record(r2)
        self.assertEqual(res2["duplicate_status"], "NEAR_DUPLICATE_CANDIDATE")
        self.assertEqual(res2["duplicate_of_evidence_id"], "EV1")

class TestPhase3RetentionAndGovernance(unittest.TestCase):
    """Tests Task 7: Retention limits, expiry evaluation, and research eligibility gate."""

    def setUp(self):
        self.retention = RetentionManager(default_days=365)

    def test_active_record_eligible(self):
        rec = {
            "retrieved_at": "2026-11-06 12:00:00",
            "eligibility_status": "ELIGIBLE",
            "collection_method": "apple_app_store_rss"
        }
        res = self.retention.evaluate_lifecycle_status(rec)
        self.assertEqual(res["deletion_status"], "ACTIVE")
        self.assertTrue(self.retention.is_eligible_for_research(res))

    def test_expired_record_excluded(self):
        rec = {
            "retrieved_at": "2020-01-01 12:00:00",
            "retention_expiry_at": "2021-01-01 12:00:00",
            "eligibility_status": "ELIGIBLE"
        }
        res = self.retention.evaluate_lifecycle_status(rec)
        self.assertEqual(res["deletion_status"], "EXPIRED")
        self.assertFalse(self.retention.is_eligible_for_research(res))

    def test_synthetic_demo_quarantined(self):
        rec = {
            "retrieved_at": "2026-11-06 12:00:00",
            "eligibility_status": "SYNTHETIC_DEMO"
        }
        res = self.retention.evaluate_lifecycle_status(rec)
        self.assertEqual(res["deletion_status"], "QUARANTINED")
        self.assertFalse(self.retention.is_eligible_for_research(res))

class TestPhase3DataQuality(unittest.TestCase):
    """Tests Task 8: Data quality assessment scoring and issue tracking."""

    def setUp(self):
        self.scorer = DataQualityScorer()

    def test_high_quality_record(self):
        rec = {
            "evidence_id": "EV1", "collection_run_id": "RUN1", "source_permission_id": "REF1",
            "app_id": "groww", "store": "apple_app_store",
            "review_text": "My SIP payment failed on HDFC bank autopay multiple times.",
            "review_created_at": "2026-11-04 12:00:00", "star_rating": 1,
            "language_detected": "en", "language_confidence": 0.85,
            "redaction_status": "CLEAN", "deletion_status": "ACTIVE", "eligibility_status": "ELIGIBLE"
        }
        res = self.scorer.assess_record(rec)
        self.assertEqual(res["data_quality_status"], "HIGH_QUALITY")
        self.assertGreaterEqual(res["data_quality_score"], 0.85)

    def test_blocked_record(self):
        rec = {"eligibility_status": "REJECTED", "deletion_status": "QUARANTINED"}
        res = self.scorer.assess_record(rec)
        self.assertEqual(res["data_quality_status"], "BLOCKED")
        self.assertEqual(res["data_quality_score"], 0.0)

class TestPhase3EndToEndPipeline(unittest.TestCase):
    """Tests Task 9: End-to-end integration across all pipeline stages."""

    def setUp(self):
        self.pipeline = ProcessingPipeline()

    def test_end_to_end_pipeline_transformation(self):
        raw = {
            "app_id": "groww",
            "store": "Apple",
            "source_record_id": "14799001",
            "review_title": "Worst &amp; Slow <b>Autopay</b>",
            "review_text": "Mera SIP payment fail ho gaya, paise kat gaye! Contact me at 9876543210.",
            "star_rating": "1",
            "review_created_at": "2026-11-04T06:49:50-07:00",
            "retrieved_at": "2026-11-06 12:00:00",
            "collection_run_id": "RUN_TEST_001",
            "source_permission_id": "PHASE3-TEST-REF",
            "eligibility_status": "ELIGIBLE"
        }

        processed = self.pipeline.process_record(raw)

        # 1. Normalization
        self.assertEqual(processed["store"], "apple_app_store")
        self.assertEqual(processed["review_title"], "Worst & Slow Autopay")
        self.assertEqual(processed["app_name"], "Groww Stocks, Mutual Fund, IPO")
        self.assertEqual(processed["star_rating"], 1)

        # 2. Language Detection
        self.assertEqual(processed["language_detected"], "hi-Latn")

        # 3. PII Minimization
        self.assertIn("[PHONE_REDACTED]", processed["review_text"])
        self.assertNotIn("9876543210", processed["review_text"])
        self.assertEqual(processed["redaction_status"], "REDACTED")

        # 4. SIP Relevance
        self.assertEqual(processed["sip_relevance_status"], "DIRECT_SIP_RELEVANT")
        self.assertEqual(processed["mentions_sip"], 1)
        self.assertEqual(processed["mentions_payment"], 1)

        # 5. Deduplication
        self.assertEqual(processed["duplicate_status"], "UNIQUE")

        # 6. Retention & Lifecycle
        self.assertEqual(processed["deletion_status"], "ACTIVE")

        # 7. Quality
        self.assertEqual(processed["data_quality_status"], "HIGH_QUALITY")
        self.assertGreaterEqual(processed["data_quality_score"], 0.85)

if __name__ == "__main__":
    unittest.main()
