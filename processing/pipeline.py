"""
Unified Processing Pipeline for Growww Discovery Engine.
Orchestrates standardization, language detection, PII redaction, SIP relevance,
deduplication, retention, and quality scoring into a reproducible pipeline.
"""
import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure local workspace packages in lib/ are available
LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from database.connection import get_db, DatabaseConnection
from processing.normalize import ReviewNormalizer, get_normalizer
from processing.language_detection import LanguageDetector, get_language_detector
from processing.pii_minimization import PIIMinimizer, get_pii_minimizer
from processing.sip_relevance import SIPRelevanceClassifier, get_sip_classifier
from processing.deduplicate import AdvancedDeduplicator, get_advanced_deduplicator
from processing.retention import RetentionManager, get_retention_manager
from processing.data_quality import DataQualityScorer, get_data_quality_scorer

class ProcessingPipeline:
    """Orchestrates end-to-end review standardization, enrichment, and quality grading."""

    def __init__(self, db: Optional[DatabaseConnection] = None):
        self.db = db or get_db()
        self.normalizer = get_normalizer()
        self.language_detector = get_language_detector()
        self.pii_minimizer = get_pii_minimizer()
        self.sip_classifier = get_sip_classifier()
        self.deduplicator = get_advanced_deduplicator()
        self.retention_manager = get_retention_manager()
        self.quality_scorer = get_data_quality_scorer()

    def process_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Runs an individual review record sequentially through all processing stages."""
        # Stage 1: Standardization & Normalization
        rec = self.normalizer.normalize_record(raw_record)

        # Stage 2: Multilingual Language Detection
        rec = self.language_detector.enrich_record(rec)

        # Stage 3: PII Minimization & Redaction
        rec = self.pii_minimizer.process_record(rec)

        # Stage 4: SIP Relevance & Coverage Screening
        rec = self.sip_classifier.enrich_record(rec)

        # Stage 5: Advanced Deduplication
        rec = self.deduplicator.evaluate_record(rec)

        # Stage 6: Retention & Deletion Lifecycle
        rec = self.retention_manager.evaluate_lifecycle_status(rec)

        # Stage 7: Data Quality Scoring
        rec = self.quality_scorer.enrich_record(rec)

        return rec

    def process_all_database_records(self) -> Dict[str, Any]:
        """
        Processes all records in SQLite reviews table and updates them in place with Phase 3 fields.
        Returns aggregate statistics dictionary.
        """
        # Ensure migration has run
        self.db.migrate_phase_3_columns()
        self.deduplicator.reset()

        stats = {
            "total_processed": 0,
            "eligible": 0,
            "blocked": 0,
            "high_quality": 0,
            "acceptable_quality": 0,
            "low_quality": 0,
            "direct_sip_relevant": 0,
            "indirect_sip_relevant": 0,
            "general_investment": 0,
            "general_app": 0,
            "irrelevant": 0,
            "languages": {},
            "redacted_pii_count": 0,
            "duplicates_detected": 0
        }

        # Fetch all existing records
        with self.db.get_connection() as conn:
            c = conn.cursor()
            rows = [dict(r) for r in c.execute("SELECT * FROM reviews ORDER BY id ASC").fetchall()]

        processed_records = []
        for raw in rows:
            proc = self.process_record(raw)
            processed_records.append(proc)

            stats["total_processed"] += 1
            if proc.get("data_quality_status") == "BLOCKED":
                stats["blocked"] += 1
            else:
                stats["eligible"] += 1

            q_status = proc.get("data_quality_status")
            if q_status == "HIGH_QUALITY":
                stats["high_quality"] += 1
            elif q_status == "ACCEPTABLE":
                stats["acceptable_quality"] += 1
            elif q_status == "LOW_QUALITY":
                stats["low_quality"] += 1

            sip_rel = proc.get("sip_relevance_status")
            if sip_rel == "DIRECT_SIP_RELEVANT":
                stats["direct_sip_relevant"] += 1
            elif sip_rel == "INDIRECT_SIP_RELEVANT":
                stats["indirect_sip_relevant"] += 1
            elif sip_rel == "GENERAL_INVESTMENT_RELEVANT":
                stats["general_investment"] += 1
            elif sip_rel == "GENERAL_APP_FEEDBACK":
                stats["general_app"] += 1
            elif sip_rel == "IRRELEVANT":
                stats["irrelevant"] += 1

            lang = proc.get("language_detected", "unknown")
            stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

            if proc.get("redaction_status") == "REDACTED":
                stats["redacted_pii_count"] += 1

            if proc.get("duplicate_status") != "UNIQUE":
                stats["duplicates_detected"] += 1

        # Batch update SQLite database
        update_fields = [
            "review_text_original", "review_text", "review_title", "content_hash",
            "content_status", "app_name", "package_name", "store",
            "language_detected", "language_confidence", "script_detected", "language_detection_method",
            "redaction_status", "redaction_categories", "pii_processed_at",
            "sip_relevance_status", "matched_query_categories", "matched_terms", "relevance_rule_version",
            "mentions_sip", "mentions_mutual_fund", "mentions_payment", "mentions_mandate",
            "mentions_autopay", "mentions_instalment", "mentions_nav", "mentions_returns",
            "mentions_units", "mentions_pause_stop", "mentions_restart", "mentions_redemption",
            "mentions_support", "mentions_kyc", "mentions_trust",
            "dedupe_group_id", "duplicate_status", "duplicate_of_evidence_id", "deduplication_method",
            "retention_expiry_at", "deletion_status", "source_policy_version",
            "data_quality_score", "data_quality_status", "data_quality_issues",
            "star_rating", "review_created_at", "retrieved_at"
        ]

        set_clause = ", ".join([f"{f} = ?" for f in update_fields])
        sql = f"UPDATE reviews SET {set_clause} WHERE id = ?"

        with self.db.get_connection() as conn:
            c = conn.cursor()
            for proc in processed_records:
                values = [proc.get(f) for f in update_fields] + [proc["id"]]
                c.execute(sql, values)

        return stats

    def export_research_datasets(
        self,
        output_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Exports clean, research-ready datasets:
          1. master_investor_feedback.csv
          2. master_investor_feedback.parquet
          3. outputs/sip_relevant_reviews.csv
          4. outputs/general_investment_reviews.csv
          5. outputs/blocked_records_report.csv
        Excludes synthetic and blocked records from research sets.
        """
        root_dir = os.path.dirname(os.path.dirname(__file__))
        outputs_dir = output_dir or os.path.join(root_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)

        with self.db.get_connection() as conn:
            c = conn.cursor()
            rows = [dict(r) for r in c.execute("SELECT * FROM reviews ORDER BY id ASC").fetchall()]

        df_all = pd.DataFrame(rows)

        # 1. Research Eligible Mask: Non-synthetic, ACTIVE, ELIGIBLE
        eligible_mask = (
            (df_all["eligibility_status"] == "ELIGIBLE") &
            (df_all["deletion_status"] == "ACTIVE") &
            (df_all["data_quality_status"] != "BLOCKED")
        )

        df_master = df_all[eligible_mask].copy()

        # Master exports in root directory
        master_csv_path = os.path.join(root_dir, "master_investor_feedback.csv")
        master_parquet_path = os.path.join(root_dir, "master_investor_feedback.parquet")

        # Disallow raw author usernames or internal DB primary key in analyst exports
        analyst_cols = [c for c in df_master.columns if c not in ("id", "created_at")]
        df_master[analyst_cols].to_csv(master_csv_path, index=False)
        try:
            df_master[analyst_cols].to_parquet(master_parquet_path, index=False)
        except Exception:
            # Fallback if pyarrow/fastparquet not present
            pass

        # 2. SIP Relevant Reviews (Direct + Indirect)
        sip_mask = eligible_mask & (df_all["sip_relevance_status"].isin(["DIRECT_SIP_RELEVANT", "INDIRECT_SIP_RELEVANT"]))
        df_sip = df_all[sip_mask].copy()
        sip_csv_path = os.path.join(outputs_dir, "sip_relevant_reviews.csv")
        df_sip[analyst_cols].to_csv(sip_csv_path, index=False)

        # 3. General Investment Reviews
        gen_inv_mask = eligible_mask & (df_all["sip_relevance_status"] == "GENERAL_INVESTMENT_RELEVANT")
        df_gen_inv = df_all[gen_inv_mask].copy()
        gen_inv_csv_path = os.path.join(outputs_dir, "general_investment_reviews.csv")
        df_gen_inv[analyst_cols].to_csv(gen_inv_csv_path, index=False)

        # 4. Blocked Records Report
        blocked_mask = ~eligible_mask
        df_blocked = df_all[blocked_mask].copy()
        blocked_csv_path = os.path.join(outputs_dir, "blocked_records_report.csv")
        # Sanitize blocked export: only output governance metadata and reasons, no raw text or PII
        blocked_safe_cols = [
            "evidence_id", "app_id", "store", "source_record_id",
            "eligibility_status", "deletion_status", "data_quality_status",
            "data_quality_issues", "source_permission_id", "retrieved_at"
        ]
        available_blocked_cols = [c for c in blocked_safe_cols if c in df_blocked.columns]
        df_blocked[available_blocked_cols].to_csv(blocked_csv_path, index=False)

        return {
            "master_csv": master_csv_path,
            "master_parquet": master_parquet_path,
            "sip_csv": sip_csv_path,
            "general_investment_csv": gen_inv_csv_path,
            "blocked_report_csv": blocked_csv_path
        }

_pipeline = None

def get_processing_pipeline() -> ProcessingPipeline:
    """Returns singleton instance of ProcessingPipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ProcessingPipeline()
    return _pipeline
