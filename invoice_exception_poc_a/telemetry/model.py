"""Formal PoC B decision-path telemetry contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


ALLOWED_DECISION_PATHS = (
    "deterministic",
    "retrieval_assisted",
    "full_reasoning",
    "hybrid",
)

DECISION_PATH_TELEMETRY_REQUIRED_FIELDS = (
    "selected_path",
    "path_transitions",
    "escalation_reason",
    "retry_count",
    "latency_ms",
    "human_review_required",
    "usage_summary",
)


@dataclass(frozen=True)
class PocBDecisionPathTelemetry:
    """Bounded run-level telemetry for PoC B decision-path observability."""

    selected_path: str
    path_transitions: list[str]
    escalation_reason: str | None
    retry_count: int
    latency_ms: float
    human_review_required: bool
    usage_summary: dict
    engine_mode: str | None = None
    path_confidence_source: str | None = None
    decision_path_version: str | None = None
    bounded_notes: list[str] = field(default_factory=list)


def build_decision_path_telemetry(
    *,
    selected_path: str,
    path_transitions: list[str],
    escalation_reason: str | None,
    retry_count: int,
    latency_ms: float,
    human_review_required: bool,
    usage_summary: dict,
    engine_mode: str | None = None,
    path_confidence_source: str | None = None,
    decision_path_version: str | None = None,
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded telemetry payload that matches the formal contract."""
    telemetry = PocBDecisionPathTelemetry(
        selected_path=selected_path,
        path_transitions=path_transitions,
        escalation_reason=escalation_reason,
        retry_count=retry_count,
        latency_ms=latency_ms,
        human_review_required=human_review_required,
        usage_summary=usage_summary,
        engine_mode=engine_mode,
        path_confidence_source=path_confidence_source,
        decision_path_version=decision_path_version,
        bounded_notes=bounded_notes or [],
    )
    return asdict(telemetry)


def validate_decision_path_telemetry(payload: dict) -> dict:
    """Validate the bounded PoC B decision-path telemetry contract."""
    missing_fields = [field for field in DECISION_PATH_TELEMETRY_REQUIRED_FIELDS if field not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Decision-path telemetry is missing required field(s): {missing}.")

    selected_path = payload["selected_path"]
    if selected_path not in ALLOWED_DECISION_PATHS:
        allowed = ", ".join(ALLOWED_DECISION_PATHS)
        raise ValueError(f"Field 'selected_path' must be one of: {allowed}.")

    path_transitions = payload["path_transitions"]
    if not isinstance(path_transitions, list) or not path_transitions:
        raise ValueError("Field 'path_transitions' must be a non-empty list of path names.")
    for transition in path_transitions:
        if transition not in ALLOWED_DECISION_PATHS:
            allowed = ", ".join(ALLOWED_DECISION_PATHS)
            raise ValueError(f"Each path transition must be one of: {allowed}.")

    if payload["escalation_reason"] is not None and (
        not isinstance(payload["escalation_reason"], str) or not payload["escalation_reason"].strip()
    ):
        raise ValueError("Field 'escalation_reason' must be null or a non-empty string.")

    retry_count = payload["retry_count"]
    if not isinstance(retry_count, int) or retry_count < 0:
        raise ValueError("Field 'retry_count' must be a non-negative integer.")

    latency_ms = payload["latency_ms"]
    if not isinstance(latency_ms, (int, float)) or latency_ms < 0:
        raise ValueError("Field 'latency_ms' must be a non-negative number.")

    if not isinstance(payload["human_review_required"], bool):
        raise ValueError("Field 'human_review_required' must be a boolean.")

    usage_summary = payload["usage_summary"]
    if not isinstance(usage_summary, dict):
        raise ValueError("Field 'usage_summary' must be a JSON object.")

    for optional_string in ("engine_mode", "path_confidence_source", "decision_path_version"):
        if optional_string in payload and payload[optional_string] is not None:
            if not isinstance(payload[optional_string], str) or not payload[optional_string].strip():
                raise ValueError(f"Field '{optional_string}' must be null or a non-empty string.")

    if "bounded_notes" in payload:
        bounded_notes = payload["bounded_notes"]
        if not isinstance(bounded_notes, list) or any(
            not isinstance(note, str) or not note.strip() for note in bounded_notes
        ):
            raise ValueError("Field 'bounded_notes' must be a list of non-empty strings.")

    return payload
