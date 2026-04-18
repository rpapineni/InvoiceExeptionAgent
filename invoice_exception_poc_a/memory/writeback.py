"""Bounded reviewed-case writeback validation and auditability helpers for PoC B."""

from __future__ import annotations

from invoice_exception_poc_a.review.feedback import validate_reviewer_feedback


REVIEWED_OUTCOME_PERSISTENCE_REQUIRED_SIGNALS = (
    "decision_path",
    "evidence_sources",
    "rule_hits",
    "similar_case_refs",
    "usage_summary",
)


REVIEWED_CASE_WRITEBACK_REQUIRED_FIELDS = (
    "predicted_label",
    "final_label",
    "predicted_owner",
    "final_owner",
    "override_flag",
    "confidence",
)


def validate_reviewed_case_writeback(
    *,
    triage_output: dict,
    reviewer_feedback: dict,
    writeback_signals: dict,
) -> dict:
    """Validate reviewed-case writeback completeness before decision-memory acceptance."""
    reviewer_feedback = validate_reviewer_feedback(reviewer_feedback)

    required_triage_fields = ("exception_type", "recommended_owner", "confidence")
    missing_triage_fields = [field_name for field_name in required_triage_fields if field_name not in triage_output]
    if missing_triage_fields:
        missing = ", ".join(missing_triage_fields)
        raise ValueError(f"Reviewed-case writeback is missing required triage field(s): {missing}.")

    predicted_label = triage_output["exception_type"]
    predicted_owner = triage_output["recommended_owner"]
    final_label = reviewer_feedback["final_label"]
    final_owner = reviewer_feedback["final_owner"]
    override_flag = reviewer_feedback["override_flag"]

    writeback_payload = {
        "predicted_label": predicted_label,
        "final_label": final_label,
        "predicted_owner": predicted_owner,
        "final_owner": final_owner,
        "override_flag": override_flag,
        "override_notes": reviewer_feedback.get("override_notes", ""),
        "decision_path": writeback_signals.get("decision_path"),
        "evidence_sources": writeback_signals.get("evidence_sources"),
        "rule_hits": writeback_signals.get("rule_hits"),
        "similar_case_refs": writeback_signals.get("similar_case_refs"),
        "confidence": triage_output["confidence"],
        "usage_summary": writeback_signals.get("usage_summary"),
    }

    missing_writeback_fields = [
        field_name
        for field_name in REVIEWED_CASE_WRITEBACK_REQUIRED_FIELDS
        if writeback_payload.get(field_name) in (None, "")
    ]
    if missing_writeback_fields:
        missing = ", ".join(missing_writeback_fields)
        raise ValueError(f"Reviewed-case writeback is missing required field(s): {missing}.")

    missing_signals = [
        field_name for field_name in REVIEWED_OUTCOME_PERSISTENCE_REQUIRED_SIGNALS if field_name not in writeback_signals
    ]
    if missing_signals:
        missing = ", ".join(missing_signals)
        raise ValueError(f"Reviewed-case writeback is missing required signal(s): {missing}.")

    if not isinstance(writeback_payload["decision_path"], str) or not writeback_payload["decision_path"].strip():
        raise ValueError("Field 'decision_path' must be a non-empty string.")

    if not isinstance(writeback_payload["confidence"], str) or not writeback_payload["confidence"].strip():
        raise ValueError("Field 'confidence' must be a non-empty string.")

    if not isinstance(writeback_payload["usage_summary"], dict):
        raise ValueError("Field 'usage_summary' must be a JSON object.")

    for list_field in ("evidence_sources", "rule_hits", "similar_case_refs"):
        value = writeback_payload[list_field]
        if not isinstance(value, list):
            raise ValueError(f"Field '{list_field}' must be a list.")
        if list_field in ("evidence_sources", "rule_hits") and not value:
            raise ValueError(f"Field '{list_field}' must be a non-empty list.")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"Field '{list_field}' must contain only non-empty strings.")

    if override_flag:
        override_notes = reviewer_feedback.get("override_notes", "")
        override_label = reviewer_feedback.get("override_label")
        override_owner = reviewer_feedback.get("override_owner")
        if not isinstance(override_notes, str) or not override_notes.strip():
            raise ValueError("Field 'override_notes' must be present when override_flag is true.")
        if not any(
            isinstance(value, str) and value.strip()
            for value in (override_label, override_owner)
        ):
            raise ValueError(
                "At least one of 'override_label' or 'override_owner' must be present when override_flag is true."
            )

    return writeback_payload
