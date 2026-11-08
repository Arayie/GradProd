-- GROWWW INVESTOR DISCOVERY ENGINE
-- POSTGRESQL PRODUCTION DDL MIGRATION SCRIPT
-- Generated automatically for Phase 8 Deployment

BEGIN;

CREATE TABLE IF NOT EXISTS "apps" (
    "id" SERIAL,
    "internal_app_id" TEXT UNIQUE NOT NULL,
    "app_name" TEXT NOT NULL,
    "developer_name" TEXT NOT NULL,
    "apple_app_id" TEXT,
    "google_play_package" TEXT,
    "apple_listing_url" TEXT,
    "google_play_listing_url" TEXT,
    "storefront" TEXT NOT NULL DEFAULT 'IN',
    "app_role" TEXT NOT NULL,
    "verification_status" TEXT NOT NULL,
    "created_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "source_routes" (
    "id" SERIAL,
    "source_id" TEXT UNIQUE NOT NULL,
    "source_name" TEXT NOT NULL,
    "store" TEXT NOT NULL,
    "collection_method" TEXT NOT NULL,
    "technical_status" TEXT NOT NULL,
    "permission_status" TEXT NOT NULL,
    "enabled" TEXT NOT NULL DEFAULT 0,
    "allowed_fields" TEXT,
    "retention_policy" TEXT,
    "last_verified_at" TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "import_batches" (
    "batch_id" TEXT,
    "original_filename" TEXT NOT NULL,
    "uploaded_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "app_id" TEXT NOT NULL,
    "store" TEXT NOT NULL,
    "source_description" TEXT,
    "permission_status" TEXT NOT NULL,
    "total_rows" INTEGER DEFAULT 0,
    "accepted_rows" INTEGER DEFAULT 0,
    "rejected_rows" INTEGER DEFAULT 0,
    "duplicate_rows" INTEGER DEFAULT 0,
    "batch_status" TEXT NOT NULL,
    PRIMARY KEY ("batch_id")
);

CREATE TABLE IF NOT EXISTS "ingestion_runs" (
    "run_id" TEXT,
    "app_id" TEXT NOT NULL,
    "store" TEXT NOT NULL,
    "collection_method" TEXT NOT NULL,
    "started_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    "completed_at" TIMESTAMP WITHOUT TIME ZONE,
    "requested_count" INTEGER DEFAULT 0,
    "received_count" INTEGER DEFAULT 0,
    "accepted_count" INTEGER DEFAULT 0,
    "rejected_count" INTEGER DEFAULT 0,
    "duplicate_count" INTEGER DEFAULT 0,
    "run_status" TEXT NOT NULL,
    "coverage_start" TIMESTAMP WITHOUT TIME ZONE,
    "coverage_end" TIMESTAMP WITHOUT TIME ZONE,
    "error_summary" TEXT,
    PRIMARY KEY ("run_id")
);

CREATE TABLE IF NOT EXISTS "collection_errors" (
    "error_id" SERIAL,
    "run_id" TEXT,
    "source_name" TEXT NOT NULL,
    "error_type" TEXT NOT NULL,
    "error_message" TEXT NOT NULL,
    "occurred_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "retry_count" INTEGER DEFAULT 0,
    "resolution_status" TEXT DEFAULT 'UNRESOLVED',
    PRIMARY KEY ("error_id")
);

CREATE TABLE IF NOT EXISTS "collection_checkpoints" (
    "id" SERIAL,
    "app_id" TEXT NOT NULL,
    "storefront" TEXT NOT NULL DEFAULT 'IN',
    "collection_method" TEXT NOT NULL,
    "last_successful_page" INTEGER DEFAULT 0,
    "last_retrieval_timestamp" TIMESTAMP WITHOUT TIME ZONE,
    "last_seen_review_id" TEXT,
    "last_coverage_date" TIMESTAMP WITHOUT TIME ZONE,
    "newest_review_date" TIMESTAMP WITHOUT TIME ZONE,
    "oldest_review_date" TIMESTAMP WITHOUT TIME ZONE,
    "total_reviews_collected" INTEGER DEFAULT 0,
    "checkpoint_data" TEXT,
    "updated_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CONSTRAINT uq_checkpoints_composite UNIQUE ("app_id", "storefront", "collection_method")
);

CREATE TABLE IF NOT EXISTS "reviews" (
    "id" SERIAL,
    "evidence_id" TEXT NOT NULL,
    "store" TEXT NOT NULL,
    "app_id" TEXT NOT NULL,
    "source_record_id" TEXT,
    "canonical_url" TEXT,
    "collection_run_id" TEXT,
    "collection_method" TEXT NOT NULL,
    "source_permission_id" TEXT,
    "review_title" TEXT,
    "review_text" TEXT NOT NULL,
    "language_original" TEXT DEFAULT 'unknown',
    "language_detected" TEXT,
    "translated_text" TEXT,
    "content_hash" TEXT NOT NULL,
    "content_status" TEXT DEFAULT 'ORIGINAL',
    "redaction_status" TEXT DEFAULT 'CLEAN',
    "storefront" TEXT DEFAULT 'IN',
    "app_version" TEXT,
    "star_rating" INTEGER NOT NULL,
    "review_created_at" TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    "review_updated_at" TIMESTAMP WITHOUT TIME ZONE,
    "retrieved_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "provider_name" TEXT,
    "store_listing_url" TEXT,
    "eligibility_status" TEXT NOT NULL DEFAULT 'PENDING',
    "source_policy_version" TEXT DEFAULT '1.0.0',
    "retention_expiry_at" TIMESTAMP WITHOUT TIME ZONE,
    "deletion_status" TEXT DEFAULT 'ACTIVE',
    "created_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "review_text_original" TEXT,
    "app_name" TEXT,
    "package_name" TEXT,
    "language_confidence" DOUBLE PRECISION DEFAULT 0.0,
    "script_detected" TEXT,
    "language_detection_method" TEXT,
    "redaction_categories" TEXT,
    "pii_processed_at" TIMESTAMP WITHOUT TIME ZONE,
    "developer_reply_present" INTEGER DEFAULT 0,
    "provider_limit_snapshot" TEXT,
    "sip_relevance_status" TEXT DEFAULT 'NEEDS_REVIEW',
    "matched_query_categories" TEXT,
    "matched_terms" TEXT,
    "relevance_rule_version" TEXT DEFAULT '1.0.0',
    "mentions_sip" INTEGER DEFAULT 0,
    "mentions_mutual_fund" INTEGER DEFAULT 0,
    "mentions_payment" INTEGER DEFAULT 0,
    "mentions_mandate" INTEGER DEFAULT 0,
    "mentions_autopay" INTEGER DEFAULT 0,
    "mentions_instalment" INTEGER DEFAULT 0,
    "mentions_nav" INTEGER DEFAULT 0,
    "mentions_returns" INTEGER DEFAULT 0,
    "mentions_units" INTEGER DEFAULT 0,
    "mentions_pause_stop" INTEGER DEFAULT 0,
    "mentions_restart" INTEGER DEFAULT 0,
    "mentions_redemption" INTEGER DEFAULT 0,
    "mentions_support" INTEGER DEFAULT 0,
    "mentions_kyc" INTEGER DEFAULT 0,
    "mentions_trust" INTEGER DEFAULT 0,
    "dedupe_group_id" TEXT,
    "duplicate_status" TEXT DEFAULT 'UNIQUE',
    "duplicate_of_evidence_id" TEXT,
    "deduplication_method" TEXT,
    "data_quality_score" DOUBLE PRECISION DEFAULT 1.0,
    "data_quality_status" TEXT DEFAULT 'HIGH_QUALITY',
    "data_quality_issues" TEXT,
    "ai_enrichment_status" TEXT DEFAULT 'NOT_ENRICHED',
    "ai_lifecycle_stage" TEXT,
    "ai_primary_pain_point" TEXT,
    "ai_pain_points" TEXT,
    "ai_confidence_score" DOUBLE PRECISION,
    "ai_confidence_tier" TEXT,
    "ai_adjudication_status" TEXT DEFAULT 'PENDING',
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "ai_evidence_log" (
    "enrichment_id" TEXT,
    "evidence_id" TEXT NOT NULL,
    "insight_id" TEXT,
    "source" TEXT NOT NULL,
    "app_name" TEXT NOT NULL,
    "store" TEXT NOT NULL,
    "source_record_id" TEXT,
    "canonical_url" TEXT,
    "review_created_at" TIMESTAMP WITHOUT TIME ZONE,
    "retrieved_at" TIMESTAMP WITHOUT TIME ZONE,
    "model_provider" TEXT NOT NULL,
    "model_id" TEXT NOT NULL,
    "prompt_id" TEXT NOT NULL,
    "prompt_version" TEXT NOT NULL,
    "prompt_hash" TEXT NOT NULL,
    "taxonomy_version" TEXT NOT NULL,
    "classification_timestamp" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "inference_latency_ms" INTEGER DEFAULT 0,
    "token_count_input" INTEGER DEFAULT 0,
    "token_count_output" INTEGER DEFAULT 0,
    "primary_research_relevance" TEXT NOT NULL,
    "lifecycle_stage" TEXT NOT NULL,
    "secondary_lifecycle_stages" TEXT,
    "investor_intent" TEXT,
    "expectations" TEXT,
    "behaviour" TEXT,
    "pain_points" TEXT,
    "triggers" TEXT,
    "outside_app_actions" TEXT,
    "reported_outcome" TEXT NOT NULL,
    "disclosed_context" TEXT,
    "confidence_overall" DOUBLE PRECISION NOT NULL,
    "confidence_lifecycle" DOUBLE PRECISION NOT NULL,
    "confidence_intent" DOUBLE PRECISION NOT NULL,
    "confidence_pain_points" DOUBLE PRECISION NOT NULL,
    "confidence_outcome" DOUBLE PRECISION NOT NULL,
    "confidence_tier" TEXT NOT NULL,
    "routing_decision" TEXT NOT NULL,
    "evidence_spans" TEXT,
    "evidence_grounding_status" TEXT NOT NULL,
    "adjudication_status" TEXT NOT NULL DEFAULT 'PENDING',
    "adjudicated_by" TEXT,
    "adjudicated_at" TIMESTAMP WITHOUT TIME ZONE,
    "adjudication_rationale" TEXT,
    "adjudicated_labels" TEXT,
    "reasoning_summary" TEXT,
    "created_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("enrichment_id")
);

CREATE TABLE IF NOT EXISTS "human_adjudications" (
    "adjudication_id" SERIAL,
    "evidence_id" TEXT NOT NULL,
    "enrichment_id" TEXT NOT NULL,
    "adjudicator_id" TEXT NOT NULL,
    "adjudication_action" TEXT NOT NULL,
    "dimension" TEXT NOT NULL,
    "original_ai_labels" TEXT,
    "adjudicated_labels" TEXT,
    "original_evidence_spans" TEXT,
    "adjudicated_evidence_spans" TEXT,
    "rationale" TEXT NOT NULL,
    "adjudicated_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("adjudication_id")
);

CREATE TABLE IF NOT EXISTS "opportunities" (
    "opportunity_id" TEXT,
    "priority_rank" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "theme_code" TEXT NOT NULL,
    "lifecycle_stage" TEXT NOT NULL,
    "target_application" TEXT NOT NULL,
    "opportunity_score" DOUBLE PRECISION NOT NULL,
    "prevalence_score" DOUBLE PRECISION NOT NULL,
    "severity_score" DOUBLE PRECISION NOT NULL,
    "lifecycle_criticality" DOUBLE PRECISION NOT NULL,
    "actionability_score" DOUBLE PRECISION NOT NULL,
    "evidence_confidence" DOUBLE PRECISION NOT NULL,
    "problem_statement" TEXT NOT NULL,
    "proposed_intervention" TEXT NOT NULL,
    "testable_hypothesis" TEXT NOT NULL,
    "exemplar_verbatim_quote" TEXT NOT NULL,
    "lifecycle_status" TEXT NOT NULL DEFAULT 'DISCOVERED',
    "primary_metric" TEXT DEFAULT '12-Month First-SIP Active Rate',
    "guardrail_metric" TEXT DEFAULT 'Mandate Bounce & Dispute Rate',
    "created_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("opportunity_id")
);

CREATE TABLE IF NOT EXISTS "opportunity_audits" (
    "audit_id" SERIAL,
    "opportunity_id" TEXT NOT NULL,
    "actor_id" TEXT NOT NULL,
    "previous_status" TEXT NOT NULL,
    "new_status" TEXT NOT NULL,
    "change_rationale" TEXT NOT NULL,
    "changed_at" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("audit_id")
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_apps_internal_id ON apps(internal_app_id);

CREATE INDEX IF NOT EXISTS idx_apps_apple_id ON apps(apple_app_id);

CREATE INDEX IF NOT EXISTS idx_apps_play_package ON apps(google_play_package);

CREATE UNIQUE INDEX IF NOT EXISTS idx_source_routes_id ON source_routes(source_id);

CREATE INDEX IF NOT EXISTS idx_reviews_app_store ON reviews(app_id, store);

CREATE INDEX IF NOT EXISTS idx_reviews_eligibility ON reviews(eligibility_status);

CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(star_rating);

CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(review_created_at);

CREATE INDEX IF NOT EXISTS idx_reviews_content_hash ON reviews(content_hash);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_app_store ON ingestion_runs(app_id, store);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(run_status);

CREATE INDEX IF NOT EXISTS idx_collection_errors_run ON collection_errors(run_id);

CREATE INDEX IF NOT EXISTS idx_import_batches_app ON import_batches(app_id);

CREATE INDEX IF NOT EXISTS idx_checkpoints_app ON collection_checkpoints(app_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_checkpoints_composite ON collection_checkpoints(app_id, storefront, collection_method);

CREATE INDEX IF NOT EXISTS idx_reviews_sip_relevance ON reviews(sip_relevance_status);

CREATE INDEX IF NOT EXISTS idx_reviews_quality_status ON reviews(data_quality_status);

CREATE INDEX IF NOT EXISTS idx_reviews_language ON reviews(language_detected);

CREATE INDEX IF NOT EXISTS idx_evidence_log_evidence_id ON ai_evidence_log(evidence_id);

CREATE INDEX IF NOT EXISTS idx_evidence_log_lifecycle ON ai_evidence_log(lifecycle_stage);

CREATE INDEX IF NOT EXISTS idx_evidence_log_confidence_tier ON ai_evidence_log(confidence_tier);

CREATE INDEX IF NOT EXISTS idx_evidence_log_adjudication ON ai_evidence_log(adjudication_status);

CREATE INDEX IF NOT EXISTS idx_evidence_log_app_name ON ai_evidence_log(app_name);

CREATE INDEX IF NOT EXISTS idx_adjudications_evidence ON human_adjudications(evidence_id);

CREATE INDEX IF NOT EXISTS idx_adjudications_enrichment ON human_adjudications(enrichment_id);

CREATE INDEX IF NOT EXISTS idx_opp_audits_opp_id ON opportunity_audits(opportunity_id);

COMMIT;
