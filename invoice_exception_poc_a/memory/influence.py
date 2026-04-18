"""Bounded retrieved-pattern influence policy helpers for PoC B."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from invoice_exception_poc_a.memory.retrieval import validate_similar_case_retrieval_artifact


RETRIEVED_PATTERN_INFLUENCE_REQUIRED_FIELDS = (
    "source_type",
    "source_ref",
    "influence_trace",
    "recommendation_influence",
    "explanation_influence",
    "confidence_influence",
    "next_actions_influence",
    "reviewer_questions_influence",
)


@dataclass(frozen=True)
class PocBRetrievedPatternInfluencePolicy:
    """Bounded advisory-only influence policy for retrieved PoC B patterns."""

    source_type: str
    source_ref: str
    influence_trace: str
    recommendation_influence: str
    explanation_influence: str
    confidence_influence: str
    next_actions_influence: str
    reviewer_questions_influence: str
    non_authority_rule: str = "retrieved_patterns_are_advisory_only"
    human_review_guardrail: str = "ap_analyst_final_decision_maker"
    influence_layer: str = "retrieved_pattern_influence_policy"
    bounded_notes: list[str] = field(default_factory=list)


def build_retrieved_pattern_influence_policy(
    *,
    retrieval_artifact: dict,
    recommendation_influence: str,
    explanation_influence: str,
    confidence_influence: str,
    next_actions_influence: str,
    reviewer_questions_influence: str,
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded influence-policy record for a retrieved artifact."""
    retrieval_artifact = validate_similar_case_retrieval_artifact(retrieval_artifact)

    policy = PocBRetrievedPatternInfluencePolicy(
        source_type=retrieval_artifact["source_type"],
        source_ref=retrieval_artifact["source_ref"],
        influence_trace=f"{retrieval_artifact['source_type']}:{retrieval_artifact['source_ref']}",
        recommendation_influence=recommendation_influence,
        explanation_influence=explanation_influence,
        confidence_influence=confidence_influence,
        next_actions_influence=next_actions_influence,
        reviewer_questions_influence=reviewer_questions_influence,
        bounded_notes=bounded_notes or ["Retrieved patterns remain traceable advisory context only."],
    )
    return asdict(policy)


def validate_retrieved_pattern_influence_policy(payload: dict) -> dict:
    """Validate the bounded retrieved-pattern influence policy."""
    missing_fields = [
        field_name for field_name in RETRIEVED_PATTERN_INFLUENCE_REQUIRED_FIELDS if field_name not in payload
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Retrieved-pattern influence policy is missing required field(s): {missing}.")

    for string_field in RETRIEVED_PATTERN_INFLUENCE_REQUIRED_FIELDS + (
        "non_authority_rule",
        "human_review_guardrail",
        "influence_layer",
    ):
        if string_field in payload:
            value = payload[string_field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Field '{string_field}' must be a non-empty string.")

    if "bounded_notes" in payload:
        bounded_notes = payload["bounded_notes"]
        if not isinstance(bounded_notes, list) or any(
            not isinstance(note, str) or not note.strip() for note in bounded_notes
        ):
            raise ValueError("Field 'bounded_notes' must be a list of non-empty strings.")

    forbidden_fragments = (
        "chain-of-thought",
        "raw_response",
        "output_text",
        "prompt",
        "provider",
        "trace dump",
    )
    for field_name in (
        "recommendation_influence",
        "explanation_influence",
        "confidence_influence",
        "next_actions_influence",
        "reviewer_questions_influence",
    ):
        lower_value = payload[field_name].lower()
        if any(fragment in lower_value for fragment in forbidden_fragments):
            raise ValueError(f"Field '{field_name}' contains disallowed verbose or unsafe content.")

    authority_fragments = (
        "auto-resolve",
        "autoroute",
        "autonomous",
        "payment action",
        "bypass human review",
        "override reviewed truth",
    )
    for field_name in (
        "recommendation_influence",
        "next_actions_influence",
        "reviewer_questions_influence",
    ):
        lower_value = payload[field_name].lower()
        if any(fragment in lower_value for fragment in authority_fragments):
            raise ValueError(f"Field '{field_name}' contains over-authoritative or unsafe influence language.")

    if payload.get("non_authority_rule") != "retrieved_patterns_are_advisory_only":
        raise ValueError("Field 'non_authority_rule' must preserve the advisory-only posture.")
    if payload.get("human_review_guardrail") != "ap_analyst_final_decision_maker":
        raise ValueError("Field 'human_review_guardrail' must preserve the AP analyst final-decision posture.")

    return payload
