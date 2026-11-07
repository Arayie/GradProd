"""
Enrichment Orchestration Service
Coordinates batch classification, evidence logging, and research dataset exports.
"""

from typing import Dict, Any, List, Optional
import os
import json
import sqlite3
import pandas as pd
import logging
from datetime import datetime

from ai.classifier import ReviewClassifier, EnrichmentResult
from ai.evidence_log_service import EvidenceLogService

logger = logging.getLogger(__name__)

class EnrichmentService:
    """Orchestrates AI enrichment over the eligible customer review dataset."""

    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            db_path = os.path.join(base_dir, "growww_discovery.db")
        self.db_path = db_path
        self.classifier = ReviewClassifier(config_path=config_path)
        self.evidence_log = EvidenceLogService(db_path=db_path)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def run_enrichment(
        self,
        target_relevance: Optional[List[str]] = None,
        limit: Optional[int] = None,
        force_reprocess: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute enrichment across target reviews in the SQLite database.
        Default targets SIP relevant and general investment reviews.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if target_relevance is None:
            target_relevance = [
                "DIRECT_SIP_RELEVANT",
                "INDIRECT_SIP_RELEVANT",
                "GENERAL_INVESTMENT_RELEVANT",
            ]

        placeholders = ",".join(["?"] * len(target_relevance))
        where_clause = f"WHERE eligibility_status = 'ELIGIBLE' AND sip_relevance_status IN ({placeholders})"
        if not force_reprocess:
            where_clause += " AND (ai_enrichment_status IS NULL OR ai_enrichment_status != 'ENRICHED')"

        query = f"""
        SELECT 
            evidence_id, app_id, app_name, store, source_record_id,
            canonical_url, review_created_at, retrieved_at,
            star_rating, review_title, review_text, review_text_original,
            language_detected, sip_relevance_status
        FROM reviews
        {where_clause}
        ORDER BY 
            CASE 
                WHEN sip_relevance_status = 'DIRECT_SIP_RELEVANT' THEN 1
                WHEN sip_relevance_status = 'INDIRECT_SIP_RELEVANT' THEN 2
                ELSE 3
            END ASC,
            review_created_at DESC
        """
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, target_relevance)
        rows = cursor.fetchall()
        reviews_to_process = [dict(r) for r in rows]
        conn.close()

        logger.info(f"Starting enrichment for {len(reviews_to_process)} reviews...")

        enriched_records = []
        errors = []
        start_time = datetime.utcnow()

        for idx, r in enumerate(reviews_to_process):
            evidence_id = r["evidence_id"]
            try:
                result = self.classifier.classify_review(
                    evidence_id=evidence_id,
                    review_text=r["review_text"],
                    app_name=r.get("app_name") or r.get("app_id", "Groww"),
                    star_rating=r.get("star_rating", 3),
                    language=r.get("language_detected", "en"),
                    review_text_original=r.get("review_text_original"),
                )

                # Persist to AI Evidence Log
                enrichment_id = self.evidence_log.log_enrichment(
                    enrichment_result=result,
                    source_metadata=r,
                )

                record_summary = {
                    **result.to_dict(),
                    "app_id": r.get("app_id"),
                    "app_name": r.get("app_name"),
                    "store": r.get("store"),
                    "star_rating": r.get("star_rating"),
                    "language_detected": r.get("language_detected"),
                    "review_created_at": r.get("review_created_at"),
                    "review_text": r.get("review_text"),
                }
                enriched_records.append(record_summary)

            except Exception as e:
                logger.error(f"Classification error for {evidence_id}: {e}")
                errors.append({
                    "evidence_id": evidence_id,
                    "app_id": r.get("app_id"),
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })

        duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            "total_targeted": len(reviews_to_process),
            "successfully_enriched": len(enriched_records),
            "failed_count": len(errors),
            "duration_seconds": round(duration, 2),
            "enriched_records": enriched_records,
            "errors": errors,
        }

    def export_phase_4_datasets(self, outputs_dir: str = "outputs") -> Dict[str, str]:
        """
        Export all required Phase 4 datasets:
        1. outputs/analysis_enriched.csv
        2. outputs/ai_evidence_log.csv
        3. outputs/model_predictions.csv
        4. outputs/classification_errors.csv
        """
        os.makedirs(outputs_dir, exist_ok=True)
        conn = self.get_connection()

        # 1. ai_evidence_log.csv
        log_path = os.path.join(outputs_dir, "ai_evidence_log.csv")
        self.evidence_log.export_csv(log_path)

        # 2. analysis_enriched.csv (joined reviews + evidence log)
        enriched_path = os.path.join(outputs_dir, "analysis_enriched.csv")
        enriched_df = pd.read_sql_query(
            """
            SELECT 
                r.evidence_id, r.app_id, r.app_name, r.store, r.star_rating,
                r.review_created_at, r.language_detected, r.sip_relevance_status,
                r.review_title, r.review_text,
                e.lifecycle_stage, e.investor_intent, e.expectations,
                e.behaviour, e.pain_points, e.triggers, e.outside_app_actions,
                e.reported_outcome, e.confidence_overall, e.confidence_tier,
                e.routing_decision, e.evidence_grounding_status,
                e.evidence_spans, e.model_provider, e.model_id,
                e.prompt_hash, e.taxonomy_version, e.adjudication_status
            FROM reviews r
            JOIN ai_evidence_log e ON r.evidence_id = e.evidence_id
            WHERE r.eligibility_status = 'ELIGIBLE'
            ORDER BY r.review_created_at DESC
            """,
            conn,
        )
        enriched_df.to_csv(enriched_path, index=False, encoding="utf-8")

        # 3. model_predictions.csv
        pred_path = os.path.join(outputs_dir, "model_predictions.csv")
        pred_df = pd.read_sql_query(
            """
            SELECT 
                evidence_id, model_provider, model_id, prompt_version,
                lifecycle_stage, investor_intent, pain_points, reported_outcome,
                confidence_overall, confidence_tier, routing_decision,
                evidence_grounding_status, inference_latency_ms
            FROM ai_evidence_log
            ORDER BY classification_timestamp DESC
            """,
            conn,
        )
        pred_df.to_csv(pred_path, index=False, encoding="utf-8")

        # 4. classification_errors.csv
        err_path = os.path.join(outputs_dir, "classification_errors.csv")
        err_df = pd.read_sql_query(
            """
            SELECT 
                e.evidence_id, e.app_name, e.confidence_overall, e.confidence_tier,
                e.routing_decision, e.evidence_grounding_status, e.reasoning_summary
            FROM ai_evidence_log e
            WHERE e.routing_decision = 'MANDATORY_REVIEW' OR e.confidence_tier = 'LOW' OR e.evidence_grounding_status = 'UNSUPPORTED'
            """,
            conn,
        )
        err_df.to_csv(err_path, index=False, encoding="utf-8")

        conn.close()

        return {
            "ai_evidence_log": log_path,
            "analysis_enriched": enriched_path,
            "model_predictions": pred_path,
            "classification_errors": err_path,
        }
