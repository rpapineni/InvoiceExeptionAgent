"""Formal PoC B knowledge-memory boundary contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


KNOWLEDGE_MEMORY_REQUIRED_FIELDS = (
    "policies",
    "sops",
    "playbooks",
    "routing_guidance",
    "reviewed_case_summaries",
)


@dataclass(frozen=True)
class PocBKnowledgeMemory:
    """Bounded retrieval-oriented business context for PoC B."""

    policies: list[dict]
    sops: list[dict]
    playbooks: list[dict]
    routing_guidance: list[dict]
    reviewed_case_summaries: list[dict]
    retrieval_scope: str = "business_context_only"
    memory_layer: str = "knowledge_memory"
    bounded_notes: list[str] = field(default_factory=list)


def build_knowledge_memory(
    *,
    policies: list[dict],
    sops: list[dict],
    playbooks: list[dict],
    routing_guidance: list[dict],
    reviewed_case_summaries: list[dict],
    retrieval_scope: str = "business_context_only",
    memory_layer: str = "knowledge_memory",
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded PoC B knowledge-memory payload."""
    knowledge_memory = PocBKnowledgeMemory(
        policies=policies,
        sops=sops,
        playbooks=playbooks,
        routing_guidance=routing_guidance,
        reviewed_case_summaries=reviewed_case_summaries,
        retrieval_scope=retrieval_scope,
        memory_layer=memory_layer,
        bounded_notes=bounded_notes or [],
    )
    return asdict(knowledge_memory)


def validate_knowledge_memory(payload: dict) -> dict:
    """Validate the bounded PoC B knowledge-memory contract."""
    missing_fields = [field for field in KNOWLEDGE_MEMORY_REQUIRED_FIELDS if field not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Knowledge memory is missing required field(s): {missing}.")

    for required_list_field in KNOWLEDGE_MEMORY_REQUIRED_FIELDS:
        value = payload[required_list_field]
        if not isinstance(value, list):
            raise ValueError(f"Field '{required_list_field}' must be a list of bounded knowledge objects.")
        for item in value:
            if not isinstance(item, dict) or not item:
                raise ValueError(
                    f"Each item in '{required_list_field}' must be a non-empty JSON object."
                )

    for optional_string in ("retrieval_scope", "memory_layer"):
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
