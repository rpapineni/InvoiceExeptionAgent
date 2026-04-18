"""Formal PoC B session-memory boundary contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


SESSION_MEMORY_REQUIRED_FIELDS = (
    "case_context",
    "tool_outputs",
    "active_reasoning_state",
    "reviewer_session_state",
)


@dataclass(frozen=True)
class PocBSessionMemory:
    """Bounded current-run session memory for PoC B."""

    case_context: dict
    tool_outputs: list[dict]
    active_reasoning_state: dict
    reviewer_session_state: dict
    session_scope: str = "current_run"
    lifetime: str = "ephemeral"
    cleanup_policy: str = "reset_at_end_of_run_or_review_session"
    bounded_notes: list[str] = field(default_factory=list)


def build_session_memory(
    *,
    case_context: dict,
    tool_outputs: list[dict],
    active_reasoning_state: dict,
    reviewer_session_state: dict,
    session_scope: str = "current_run",
    lifetime: str = "ephemeral",
    cleanup_policy: str = "reset_at_end_of_run_or_review_session",
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded PoC B session-memory payload."""
    session_memory = PocBSessionMemory(
        case_context=case_context,
        tool_outputs=tool_outputs,
        active_reasoning_state=active_reasoning_state,
        reviewer_session_state=reviewer_session_state,
        session_scope=session_scope,
        lifetime=lifetime,
        cleanup_policy=cleanup_policy,
        bounded_notes=bounded_notes or [],
    )
    return asdict(session_memory)


def validate_session_memory(payload: dict) -> dict:
    """Validate the bounded PoC B session-memory contract."""
    missing_fields = [field for field in SESSION_MEMORY_REQUIRED_FIELDS if field not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Session memory is missing required field(s): {missing}.")

    for required_dict_field in ("case_context", "active_reasoning_state", "reviewer_session_state"):
        value = payload[required_dict_field]
        if not isinstance(value, dict) or not value:
            raise ValueError(f"Field '{required_dict_field}' must be a non-empty JSON object.")

    tool_outputs = payload["tool_outputs"]
    if not isinstance(tool_outputs, list):
        raise ValueError("Field 'tool_outputs' must be a list of bounded tool-output records.")
    for tool_output in tool_outputs:
        if not isinstance(tool_output, dict) or not tool_output:
            raise ValueError("Each item in 'tool_outputs' must be a non-empty JSON object.")

    for optional_string in ("session_scope", "lifetime", "cleanup_policy"):
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
