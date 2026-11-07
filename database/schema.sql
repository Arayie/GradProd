-- Growww AI-Powered Investor Discovery Engine
-- Database Schema Definition (SQLite 3 compatible, portable to PostgreSQL/Supabase)
-- Version: 1.0.0 (Phase 1 Baseline)

PRAGMA foreign_keys = ON;

-- =========================================================================
-- TABLE 1: apps
-- Stores verified target and competitor investment applications
-- =========================================================================
CREATE TABLE IF NOT EXISTS apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_app_id TEXT UNIQUE NOT NULL,
    app_name TEXT NOT NULL,
    developer_name TEXT NOT NULL,
    apple_app_id TEXT,
    google_play_package TEXT,
    apple_listing_url TEXT,
    google_play_listing_url TEXT,
    storefront TEXT NOT NULL DEFAULT 'IN',
    app_role TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_apps_internal_id ON apps(internal_app_id);
CREATE INDEX IF NOT EXISTS idx_apps_apple_id ON apps(apple_app_id);
CREATE INDEX IF NOT EXISTS idx_apps_play_package ON apps(google_play_package);

-- =========================================================================
-- TABLE 2: source_routes
-- Governance registry for public and owner review ingestion routes
-- =========================================================================
CREATE TABLE IF NOT EXISTS source_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    source_name TEXT NOT NULL,
    store TEXT NOT NULL,
    collection_method TEXT NOT NULL,
    technical_status TEXT NOT NULL,
    permission_status TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 0,
    allowed_fields TEXT,
    retention_policy TEXT,
    last_verified_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source_routes_id ON source_routes(source_id);

-- =========================================================================
-- TABLE 3: reviews
-- Foundational canonical review repository
-- =========================================================================
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT UNIQUE NOT NULL,
    store TEXT NOT NULL,                       -- 'apple_app_store', 'google_play'
    app_id TEXT NOT NULL REFERENCES apps(internal_app_id) ON DELETE RESTRICT,
    source_record_id TEXT,                     -- Platform specific review identifier
    canonical_url TEXT,
    collection_run_id TEXT,
    collection_method TEXT NOT NULL,           -- 'manual_csv_import', 'apple_rss'
    source_permission_id TEXT,
    
    -- Content attributes
    review_title TEXT,
    review_text TEXT NOT NULL,
    review_text_original TEXT,                 -- Immutable raw review text
    language_original TEXT DEFAULT 'unknown',
    language_detected TEXT,
    language_confidence REAL DEFAULT 0.0,
    script_detected TEXT,                      -- 'LATIN', 'DEVANAGARI', 'MIXED', 'UNKNOWN'
    language_detection_method TEXT,
    translated_text TEXT,
    content_hash TEXT NOT NULL,
    content_status TEXT DEFAULT 'ORIGINAL',
    redaction_status TEXT DEFAULT 'CLEAN',
    redaction_categories TEXT,                 -- JSON array of redacted PII categories
    pii_processed_at TIMESTAMP,
    
    -- Store metadata
    app_name TEXT,
    package_name TEXT,
    storefront TEXT DEFAULT 'IN',
    app_version TEXT,
    star_rating INTEGER NOT NULL CHECK(star_rating BETWEEN 1 AND 5),
    developer_reply_present INTEGER DEFAULT 0,
    review_created_at TIMESTAMP NOT NULL,
    review_updated_at TIMESTAMP,
    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provider_name TEXT,
    store_listing_url TEXT,
    provider_limit_snapshot TEXT,

    -- SIP Relevance & Coverage Screening (Phase 3)
    sip_relevance_status TEXT DEFAULT 'NEEDS_REVIEW',  -- DIRECT_SIP_RELEVANT, INDIRECT_SIP_RELEVANT, etc.
    matched_query_categories TEXT,                     -- JSON array of matched query categories
    matched_terms TEXT,                                -- JSON array of matched terms
    relevance_rule_version TEXT DEFAULT '1.0.0',
    mentions_sip INTEGER DEFAULT 0,
    mentions_mutual_fund INTEGER DEFAULT 0,
    mentions_payment INTEGER DEFAULT 0,
    mentions_mandate INTEGER DEFAULT 0,
    mentions_autopay INTEGER DEFAULT 0,
    mentions_instalment INTEGER DEFAULT 0,
    mentions_nav INTEGER DEFAULT 0,
    mentions_returns INTEGER DEFAULT 0,
    mentions_units INTEGER DEFAULT 0,
    mentions_pause_stop INTEGER DEFAULT 0,
    mentions_restart INTEGER DEFAULT 0,
    mentions_redemption INTEGER DEFAULT 0,
    mentions_support INTEGER DEFAULT 0,
    mentions_kyc INTEGER DEFAULT 0,
    mentions_trust INTEGER DEFAULT 0,

    -- Advanced Deduplication (Phase 3)
    dedupe_group_id TEXT,
    duplicate_status TEXT DEFAULT 'UNIQUE',            -- UNIQUE, DUPLICATE_SOURCE_ID, DUPLICATE_HASH, NEAR_DUPLICATE_CANDIDATE
    duplicate_of_evidence_id TEXT,
    deduplication_method TEXT,

    -- Data Quality (Phase 3)
    data_quality_score REAL DEFAULT 1.0,               -- 0.0 to 1.0
    data_quality_status TEXT DEFAULT 'HIGH_QUALITY',    -- HIGH_QUALITY, ACCEPTABLE, LOW_QUALITY, BLOCKED
    data_quality_issues TEXT,                          -- JSON array of quality issues
    
    -- Governance and eligibility
    eligibility_status TEXT NOT NULL DEFAULT 'PENDING',  -- 'ELIGIBLE', 'PENDING', 'REJECTED', 'SYNTHETIC_DEMO'
    source_policy_version TEXT DEFAULT '1.0.0',
    retention_expiry_at TIMESTAMP,
    deletion_status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Uniqueness constraint: Same app, store, and source review ID cannot be duplicated
    CONSTRAINT uq_app_store_source_record UNIQUE (app_id, store, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_app_store ON reviews(app_id, store);
CREATE INDEX IF NOT EXISTS idx_reviews_eligibility ON reviews(eligibility_status);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(star_rating);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(review_created_at);
CREATE INDEX IF NOT EXISTS idx_reviews_content_hash ON reviews(content_hash);
CREATE INDEX IF NOT EXISTS idx_reviews_sip_relevance ON reviews(sip_relevance_status);
CREATE INDEX IF NOT EXISTS idx_reviews_quality_status ON reviews(data_quality_status);
CREATE INDEX IF NOT EXISTS idx_reviews_language ON reviews(language_detected);

-- =========================================================================
-- TABLE 4: ingestion_runs
-- Audit log for automated and batch review collection runs
-- =========================================================================
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    app_id TEXT NOT NULL,
    store TEXT NOT NULL,
    collection_method TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    requested_count INTEGER DEFAULT 0,
    received_count INTEGER DEFAULT 0,
    accepted_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0,
    run_status TEXT NOT NULL,                  -- 'STARTED', 'COMPLETED', 'FAILED', 'PARTIAL'
    coverage_start TIMESTAMP,
    coverage_end TIMESTAMP,
    error_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_app_store ON ingestion_runs(app_id, store);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(run_status);

-- =========================================================================
-- TABLE 5: collection_errors
-- Diagnostic failure logs for connector troubleshooting
-- =========================================================================
CREATE TABLE IF NOT EXISTS collection_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    source_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    resolution_status TEXT DEFAULT 'UNRESOLVED'
);

CREATE INDEX IF NOT EXISTS idx_collection_errors_run ON collection_errors(run_id);

-- =========================================================================
-- TABLE 6: import_batches
-- Metadata tracking for manual CSV file ingestion sessions
-- =========================================================================
CREATE TABLE IF NOT EXISTS import_batches (
    batch_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    app_id TEXT NOT NULL,
    store TEXT NOT NULL,
    source_description TEXT,
    permission_status TEXT NOT NULL,          -- 'APPROVED', 'PENDING_VERIFICATION', 'REJECTED'
    total_rows INTEGER DEFAULT 0,
    accepted_rows INTEGER DEFAULT 0,
    rejected_rows INTEGER DEFAULT 0,
    duplicate_rows INTEGER DEFAULT 0,
    batch_status TEXT NOT NULL                -- 'PROCESSING', 'COMPLETED', 'FAILED'
);

CREATE INDEX IF NOT EXISTS idx_import_batches_app ON import_batches(app_id);

-- =========================================================================
-- TABLE 7: collection_checkpoints
-- Ingestion state markers for resuming runs and incremental collection
-- =========================================================================
CREATE TABLE IF NOT EXISTS collection_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT NOT NULL REFERENCES apps(internal_app_id) ON DELETE CASCADE,
    storefront TEXT NOT NULL DEFAULT 'IN',
    collection_method TEXT NOT NULL,
    last_successful_page INTEGER DEFAULT 0,
    last_retrieval_timestamp TIMESTAMP,
    last_seen_review_id TEXT,
    last_coverage_date TIMESTAMP,
    newest_review_date TIMESTAMP,
    oldest_review_date TIMESTAMP,
    total_reviews_collected INTEGER DEFAULT 0,
    checkpoint_data TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_checkpoint_app_store_method UNIQUE (app_id, storefront, collection_method)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_app ON collection_checkpoints(app_id);

-- =========================================================================
-- TABLE 8: ai_evidence_log (Phase 4)
-- Traceable, reproducible audit trail for AI enrichments & evidence spans
-- =========================================================================
CREATE TABLE IF NOT EXISTS ai_evidence_log (
    enrichment_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL REFERENCES reviews(evidence_id),
    insight_id TEXT,
    source TEXT NOT NULL,
    app_name TEXT NOT NULL,
    store TEXT NOT NULL,
    source_record_id TEXT,
    canonical_url TEXT,
    review_created_at TIMESTAMP,
    retrieved_at TIMESTAMP,
    model_provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    classification_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    inference_latency_ms INTEGER DEFAULT 0,
    token_count_input INTEGER DEFAULT 0,
    token_count_output INTEGER DEFAULT 0,
    primary_research_relevance TEXT NOT NULL,
    lifecycle_stage TEXT NOT NULL,
    secondary_lifecycle_stages TEXT,
    investor_intent TEXT,
    expectations TEXT,
    behaviour TEXT,
    pain_points TEXT,
    triggers TEXT,
    outside_app_actions TEXT,
    reported_outcome TEXT NOT NULL,
    disclosed_context TEXT,
    confidence_overall REAL NOT NULL,
    confidence_lifecycle REAL NOT NULL,
    confidence_intent REAL NOT NULL,
    confidence_pain_points REAL NOT NULL,
    confidence_outcome REAL NOT NULL,
    confidence_tier TEXT NOT NULL,
    routing_decision TEXT NOT NULL,
    evidence_spans TEXT,
    evidence_grounding_status TEXT NOT NULL,
    adjudication_status TEXT NOT NULL DEFAULT 'PENDING',
    adjudicated_by TEXT,
    adjudicated_at TIMESTAMP,
    adjudication_rationale TEXT,
    adjudicated_labels TEXT,
    reasoning_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_log_evidence_id ON ai_evidence_log(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_log_lifecycle ON ai_evidence_log(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_evidence_log_confidence_tier ON ai_evidence_log(confidence_tier);
CREATE INDEX IF NOT EXISTS idx_evidence_log_adjudication ON ai_evidence_log(adjudication_status);
CREATE INDEX IF NOT EXISTS idx_evidence_log_app_name ON ai_evidence_log(app_name);

-- =========================================================================
-- TABLE 9: human_adjudications (Phase 4)
-- Human reviewer actions and ground-truth validation records
-- =========================================================================
CREATE TABLE IF NOT EXISTS human_adjudications (
    adjudication_id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT NOT NULL REFERENCES reviews(evidence_id),
    enrichment_id TEXT NOT NULL REFERENCES ai_evidence_log(enrichment_id),
    adjudicator_id TEXT NOT NULL,
    adjudication_action TEXT NOT NULL,
    dimension TEXT NOT NULL,
    original_ai_labels TEXT,
    adjudicated_labels TEXT,
    original_evidence_spans TEXT,
    adjudicated_evidence_spans TEXT,
    rationale TEXT NOT NULL,
    adjudicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_adjudications_evidence ON human_adjudications(evidence_id);
CREATE INDEX IF NOT EXISTS idx_adjudications_enrichment ON human_adjudications(enrichment_id);

-- =========================================================================
-- TABLE 10: opportunities (Phase 6)
-- Prioritized product intervention backlog with multi-factor scoring
-- =========================================================================
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    priority_rank INTEGER NOT NULL,
    title TEXT NOT NULL,
    theme_code TEXT NOT NULL,
    lifecycle_stage TEXT NOT NULL,
    target_application TEXT NOT NULL,
    opportunity_score REAL NOT NULL,
    prevalence_score REAL NOT NULL,
    severity_score REAL NOT NULL,
    lifecycle_criticality REAL NOT NULL,
    actionability_score REAL NOT NULL,
    evidence_confidence REAL NOT NULL,
    problem_statement TEXT NOT NULL,
    proposed_intervention TEXT NOT NULL,
    testable_hypothesis TEXT NOT NULL,
    exemplar_verbatim_quote TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL DEFAULT 'DISCOVERED',
    primary_metric TEXT DEFAULT '12-Month First-SIP Active Rate',
    guardrail_metric TEXT DEFAULT 'Mandate Bounce & Dispute Rate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================================
-- TABLE 11: opportunity_audits (Phase 6)
-- Immutable audit log for product opportunity lifecycle status changes
-- =========================================================================
CREATE TABLE IF NOT EXISTS opportunity_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
    actor_id TEXT NOT NULL,
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    change_rationale TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_opp_audits_opp_id ON opportunity_audits(opportunity_id);
