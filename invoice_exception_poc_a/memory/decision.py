"""Formal PoC B decision-memory boundary contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


DECISION_MEMORY_REQUIRED_FIELDS = (
    "reviewed_outcome",
    "final_label",
    "final_owner",
    "override_history",
    "vendor_exception_profile",
    "routing_tendencies",
    "confidence_history",
    "remediation_patterns",
)

MINIMUM_WRITEBACK_COMPATIBILITY_FIELDS = (
    "predicted_label",
    "predicted_owner",
    "override_flag",
    "override_notes",
    "decision_path",
    "evidence_sources",
    "rule_hits",
    "similar_case_refs",
    "confidence",
    "usage_summary",
)


@dataclass(frozen=True)
class PocBDecisionMemory:
    """Bounded structured and queryable reviewed-outcome intelligence for PoC B."""

    reviewed_outcome: dict
    final_label: str
    final_owner: str
    override_history: list[dict]
    vendor_exception_profile: dict
    routing_tendencies: list[dict]
    confidence_history: list[dict]
    remediation_patterns: list[dict]
    writeback_compatibility: dict
    memory_layer: str = "decision_memory"
    queryable_semantics: str = "structured_reviewed_outcome_intelligence"
    bounded_notes: list[str] = field(default_factory=list)


def build_decision_memory(
    *,
    reviewed_outcome: dict,
    final_label: str,
    final_owner: str,
    override_history: list[dict],
    vendor_exception_profile: dict,
    routing_tendencies: list[dict],
    confidence_history: list[dict],
    remediation_patterns: list[dict],
    writeback_compatibility: dict,
    memory_layer: str = "decision_memory",
    queryable_semantics: str = "structured_reviewed_outcome_intelligence",
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded PoC B decision-memory payload."""
    decision_memory = PocBDecisionMemory(
        reviewed_outcome=reviewed_outcome,
        final_label=final_label,
        final_owner=final_owner,
        override_history=override_history,
        vendor_exception_profile=vendor_exception_profile,
        routing_tendencies=routing_tendencies,
        confidence_history=confidence_history,
        remediation_patterns=remediation_patterns,
        writeback_compatibility=writeback_compatibility,
        memory_layer=memory_layer,
        queryable_semantics=queryable_semantics,
        bounded_notes=bounded_notes or [],
    )
    return asdict(decision_memory)


def validate_decision_memory(payload: dict) -> dict:
    """Validate the bounded PoC B decision-memory contract."""
    missing_fields = [field_name for field_name in DECISION_MEMORY_REQUIRED_FIELDS if field_name not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Decision memory is missing required field(s): {missing}.")

    if "writeback_compatibility" not in payload:
        raise ValueError("Decision memory is missing required field(s): writeback_compatibility.")

    if not isinstance(payload["reviewed_outcome"], dict) or not payload["reviewed_outcome"]:
        raise ValueError("Field 'reviewed_outcome' must be a non-empty JSON object.")

    for string_field in ("final_label", "final_owner"):
        value = payload[string_field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{string_field}' must be a non-empty string.")

    if not isinstance(payload["vendor_exception_profile"], dict) or not payload["vendor_exception_profile"]:
        raise ValueError("Field 'vendor_exception_profile' must be a non-empty JSON object.")

    for list_field in ("override_history", "routing_tendencies", "confidence_history", "remediation_patterns"):
        value = payload[list_field]
        if not isinstance(value, list):
            raise ValueError(f"Field '{list_field}' must be a list of bounded decision-memory records.")
        for item in value:
            if not isinstance(item, dict) or not item:
                raise ValueError(f"Each item in '{list_field}' must be a non-empty JSON object.")

    writeback_compatibility = payload["writeback_compatibility"]
    if not isinstance(writeback_compatibility, dict):
        raise ValueError("Field 'writeback_compatibility' must be a JSON object.")
    missing_writeback_fields = [
        field_name for field_name in MINIMUM_WRITEBACK_COMPATIBILITY_FIELDS if field_name not in writeback_compatibility
    ]
    if missing_writeback_fields:
        missing = ", ".join(missing_writeback_fields)
        raise ValueError(
            f"Field 'writeback_compatibility' is missing required writeback signal(s): {missing}."
        )

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
