"""Formal PoC B reviewer feedback capture flow contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


REVIEWER_FEEDBACK_REQUIRED_FIELDS = (
    "predicted_label",
    "predicted_owner",
    "accept_as_is",
    "final_label",
    "final_owner",
    "reviewer_notes",
    "ambiguous_or_novel_flag",
    "precedent_usefulness_flag",
)


@dataclass(frozen=True)
class PocBReviewerFeedback:
    """Bounded structured reviewer feedback captured after first-pass triage."""

    predicted_label: str
    predicted_owner: str
    accept_as_is: bool
    final_label: str
    final_owner: str
    reviewer_notes: str
    ambiguous_or_novel_flag: bool
    precedent_usefulness_flag: bool
    override_label: str | None = None
    override_owner: str | None = None
    override_flag: bool = False
    override_notes: str = ""
    review_action: str = "review_completed"
    feedback_scope: str = "human_review_boundary"
    bounded_notes: list[str] = field(default_factory=list)


def build_reviewer_feedback(
    *,
    predicted_label: str,
    predicted_owner: str,
    accept_as_is: bool,
    final_label: str,
    final_owner: str,
    reviewer_notes: str,
    ambiguous_or_novel_flag: bool,
    precedent_usefulness_flag: bool,
    override_label: str | None = None,
    override_owner: str | None = None,
    override_notes: str = "",
    review_action: str = "review_completed",
    feedback_scope: str = "human_review_boundary",
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded reviewer feedback payload."""
    override_flag = (final_label != predicted_label) or (final_owner != predicted_owner)
    feedback = PocBReviewerFeedback(
        predicted_label=predicted_label,
        predicted_owner=predicted_owner,
        accept_as_is=accept_as_is,
        final_label=final_label,
        final_owner=final_owner,
        reviewer_notes=reviewer_notes,
        ambiguous_or_novel_flag=ambiguous_or_novel_flag,
        precedent_usefulness_flag=precedent_usefulness_flag,
        override_label=override_label,
        override_owner=override_owner,
        override_flag=override_flag,
        override_notes=override_notes,
        review_action=review_action,
        feedback_scope=feedback_scope,
        bounded_notes=bounded_notes or [],
    )
    return asdict(feedback)


def validate_reviewer_feedback(payload: dict) -> dict:
    """Validate the bounded reviewer feedback capture contract."""
    missing_fields = [field_name for field_name in REVIEWER_FEEDBACK_REQUIRED_FIELDS if field_name not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Reviewer feedback is missing required field(s): {missing}.")

    for string_field in ("predicted_label", "predicted_owner", "final_label", "final_owner", "reviewer_notes"):
        value = payload[string_field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Field '{string_field}' must be a non-empty string.")

    for bool_field in ("accept_as_is", "ambiguous_or_novel_flag", "precedent_usefulness_flag"):
        if not isinstance(payload[bool_field], bool):
            raise ValueError(f"Field '{bool_field}' must be a boolean.")

    override_flag = (payload["final_label"] != payload["predicted_label"]) or (
        payload["final_owner"] != payload["predicted_owner"]
    )

    if "override_flag" in payload and payload["override_flag"] != override_flag:
        raise ValueError("Field 'override_flag' must match the predicted-versus-final distinction.")

    if payload["accept_as_is"] and override_flag:
        raise ValueError("Field 'accept_as_is' cannot be true when label or owner was overridden.")

    if override_flag and not isinstance(payload.get("override_notes"), str):
        raise ValueError("Field 'override_notes' must be a string when overrides are present.")

    for optional_string in ("override_label", "override_owner", "override_notes", "review_action", "feedback_scope"):
        if optional_string in payload and payload[optional_string] is not None:
            value = payload[optional_string]
            if not isinstance(value, str):
                raise ValueError(f"Field '{optional_string}' must be null or a string.")
            if optional_string in ("review_action", "feedback_scope") and not value.strip():
                raise ValueError(f"Field '{optional_string}' must be null or a non-empty string.")

    if "bounded_notes" in payload:
        bounded_notes = payload["bounded_notes"]
        if not isinstance(bounded_notes, list) or any(
            not isinstance(note, str) or not note.strip() for note in bounded_notes
        ):
            raise ValueError("Field 'bounded_notes' must be a list of non-empty strings.")

    return payload
