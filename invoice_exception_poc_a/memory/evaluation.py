"""Formal PoC B evaluation-memory boundary contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


EVALUATION_MEMORY_REQUIRED_FIELDS = (
    "benchmark_case_set",
    "repeated_pattern_case_set",
    "replay_cases",
    "regression_history",
    "failure_taxonomy",
)


@dataclass(frozen=True)
class PocBEvaluationMemory:
    """Bounded structured and queryable evaluation artifacts for PoC B."""

    benchmark_case_set: list[dict]
    repeated_pattern_case_set: list[dict]
    replay_cases: list[dict]
    regression_history: list[dict]
    failure_taxonomy: list[dict]
    memory_layer: str = "evaluation_memory"
    queryable_semantics: str = "structured_evaluation_artifacts"
    bounded_notes: list[str] = field(default_factory=list)


def build_evaluation_memory(
    *,
    benchmark_case_set: list[dict],
    repeated_pattern_case_set: list[dict],
    replay_cases: list[dict],
    regression_history: list[dict],
    failure_taxonomy: list[dict],
    memory_layer: str = "evaluation_memory",
    queryable_semantics: str = "structured_evaluation_artifacts",
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded PoC B evaluation-memory payload."""
    evaluation_memory = PocBEvaluationMemory(
        benchmark_case_set=benchmark_case_set,
        repeated_pattern_case_set=repeated_pattern_case_set,
        replay_cases=replay_cases,
        regression_history=regression_history,
        failure_taxonomy=failure_taxonomy,
        memory_layer=memory_layer,
        queryable_semantics=queryable_semantics,
        bounded_notes=bounded_notes or [],
    )
    return asdict(evaluation_memory)


def validate_evaluation_memory(payload: dict) -> dict:
    """Validate the bounded PoC B evaluation-memory contract."""
    missing_fields = [field_name for field_name in EVALUATION_MEMORY_REQUIRED_FIELDS if field_name not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Evaluation memory is missing required field(s): {missing}.")

    for list_field in EVALUATION_MEMORY_REQUIRED_FIELDS:
        value = payload[list_field]
        if not isinstance(value, list):
            raise ValueError(f"Field '{list_field}' must be a list of bounded evaluation artifacts.")
        for item in value:
            if not isinstance(item, dict) or not item:
                raise ValueError(f"Each item in '{list_field}' must be a non-empty JSON object.")

    for optional_string in ("memory_layer", "queryable_semantics"):
        if optional_string in payload and payload[optional_string] is not None:
            value = payload[optional_string]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Field '{optional_string}' must be null or a non-empty string.")

    if "bounded_notes" in payload:
        bounded_notes = payload["bounded_notes"]
        if not isinstance(bounded_notes, list) or any(
            not isinstance(note, str) or not note.strip() for note in bounded_notes
        ):
            raise ValueError("Field 'bounded_notes' must be a list of non-empty strings.")

    return payload
