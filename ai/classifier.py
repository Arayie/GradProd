"""
Review Classifier Pipeline
Orchestrates prompt formatting, LLM inference, schema validation, exact evidence grounding,
and confidence routing for qualitative investor discovery.
"""

from typing import Dict, Any, Optional, Tuple, List
import logging
from dataclasses import dataclass, asdict

from ai.prompt_manager import PromptManager
from ai.llm_client import LLMClient
from ai.schema_validator import SchemaValidator
from ai.evidence_extractor import EvidenceExtractor
from ai.confidence import ConfidenceRouter

logger = logging.getLogger(__name__)

@dataclass
class EnrichmentResult:
    """Structured output container for an enriched review record."""
    evidence_id: str
    primary_research_relevance: str
    lifecycle_stage: str
    secondary_lifecycle_stages: List[str]
    investor_intent: List[str]
    expectations: List[str]
    behaviour: List[str]
    pain_points: List[str]
    triggers: List[str]
    outside_app_actions: List[str]
    reported_outcome: str
    disclosed_context: Dict[str, str]
    confidence_overall: float
    confidence_lifecycle: float
    confidence_intent: float
    confidence_pain_points: float
    confidence_outcome: float
    confidence_tier: str
    routing_decision: str
    routing_reasons: List[str]
    evidence_spans: Dict[str, Optional[str]]
    evidence_grounding_status: str
    grounding_metadata: Dict[str, Any]
    model_provider: str
    model_id: str
    prompt_hash: str
    prompt_version: str
    taxonomy_version: str
    reasoning_summary: str
    inference_latency_ms: int
    token_count_input: int
    token_count_output: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ReviewClassifier:
    """End-to-end classifier for Indian investment application reviews."""

    def __init__(self, config_path: Optional[str] = None):
        self.prompt_manager = PromptManager()
        self.llm_client = LLMClient(config_path=config_path)
        self.validator = SchemaValidator()
        self.taxonomy_version = "2.0.0"

    def classify_review(
        self,
        evidence_id: str,
        review_text: str,
        app_name: str = "Groww",
        star_rating: int = 3,
        language: str = "en",
        review_text_original: Optional[str] = None,
    ) -> EnrichmentResult:
        """
        Classify a single customer review with full evidence validation and confidence routing.
        """
        # 1. Prepare sanitized prompts
        sys_prompt, user_prompt, prompt_hash, prompt_version = self.prompt_manager.render_prompts(
            evidence_id=evidence_id,
            review_text=review_text,
            app_name=app_name,
            star_rating=star_rating,
        )

        # 2. Invoke Model / Deterministic Engine
        raw_output = self.llm_client.classify(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            evidence_id=evidence_id,
            review_text=review_text,
            app_name=app_name,
            star_rating=star_rating,
            language=language,
        )

        metadata = raw_output.pop("_metadata", {})
        model_provider = metadata.get("model_provider", "Deterministic NLP Engine")
        model_id = metadata.get("model_id", "rule-nlp-v2.0")
        latency_ms = metadata.get("latency_ms", 0)
        tokens_in = metadata.get("token_count_input", 0)
        tokens_out = metadata.get("token_count_output", 0)

        # 3. Schema Validation & Normalization
        is_valid, validation_errors, validated_data = self.validator.validate(raw_output)
        if not is_valid:
            logger.warning(f"Schema validation warnings for {evidence_id}: {validation_errors}")

        # 4. Exact Verbatim Evidence Verification
        candidate_spans = validated_data.get("evidence_spans", {})
        verified_spans, grounding_status, grounding_meta = EvidenceExtractor.verify_and_ground_spans(
            evidence_spans=candidate_spans,
            review_text=review_text,
            original_text=review_text_original,
            assigned_labels=validated_data.get("pain_points", []),
        )

        # 5. Confidence Scoring and Human Review Routing
        conf_scores = validated_data.get("confidence_scores", {})
        tier, routing_decision, routing_reasons = ConfidenceRouter.evaluate_routing(
            confidence_scores=conf_scores,
            pain_points=validated_data.get("pain_points", []),
            lifecycle_stage=validated_data.get("lifecycle_stage", "UNKNOWN"),
            grounding_status=grounding_status,
        )

        return EnrichmentResult(
            evidence_id=evidence_id,
            primary_research_relevance=validated_data["primary_research_relevance"],
            lifecycle_stage=validated_data["lifecycle_stage"],
            secondary_lifecycle_stages=validated_data["secondary_lifecycle_stages"],
            investor_intent=validated_data["investor_intent"],
            expectations=validated_data["expectations"],
            behaviour=validated_data["behaviour"],
            pain_points=validated_data["pain_points"],
            triggers=validated_data["triggers"],
            outside_app_actions=validated_data["outside_app_actions"],
            reported_outcome=validated_data["reported_outcome"],
            disclosed_context=validated_data["disclosed_context"],
            confidence_overall=conf_scores.get("overall", 0.70),
            confidence_lifecycle=conf_scores.get("lifecycle_stage", 0.70),
            confidence_intent=conf_scores.get("investor_intent", 0.70),
            confidence_pain_points=conf_scores.get("pain_points", 0.70),
            confidence_outcome=conf_scores.get("reported_outcome", 0.70),
            confidence_tier=tier,
            routing_decision=routing_decision,
            routing_reasons=routing_reasons,
            evidence_spans=verified_spans,
            evidence_grounding_status=grounding_status,
            grounding_metadata=grounding_meta,
            model_provider=model_provider,
            model_id=model_id,
            prompt_hash=prompt_hash,
            prompt_version=prompt_version,
            taxonomy_version=self.taxonomy_version,
            reasoning_summary=validated_data.get("reasoning_summary", ""),
            inference_latency_ms=latency_ms,
            token_count_input=tokens_in,
            token_count_output=tokens_out,
        )
