"""Bounded reviewed-case summary helpers for PoC B."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from invoice_exception_poc_a.memory.decision import validate_decision_memory


REVIEWED_CASE_SUMMARY_REQUIRED_FIELDS = (
    "normalized_case_pattern",
    "final_disposition",
    "override_reason_summary",
    "routing_precedent",
    "vendor_specific_notes",
    "confidence_hint",
)


@dataclass(frozen=True)
class PocBReviewedCaseSummary:
    """Concise retrieval-friendly summary of a reviewed case for later reuse."""

    normalized_case_pattern: str
    final_disposition: str
    override_reason_summary: str
    routing_precedent: str
    vendor_specific_notes: str
    confidence_hint: str
    summary_kind: str = "reviewed_case_summary"
    retrieval_friendly_semantics: str = "concise_structured_reuse"
    bounded_notes: list[str] = field(default_factory=list)


def build_reviewed_case_summary(
    *,
    decision_memory: dict,
    bounded_notes: list[str] | None = None,
) -> dict:
    """Build a bounded reviewed-case summary from a validated decision-memory record."""
    decision_memory = validate_decision_memory(decision_memory)

    reviewed_outcome = decision_memory["reviewed_outcome"]
    writeback_compatibility = decision_memory["writeback_compatibility"]
    vendor_profile = decision_memory["vendor_exception_profile"]

    predicted_label = reviewed_outcome["predicted_label"]
    final_label = reviewed_outcome["final_label"]
    final_owner = reviewed_outcome["final_owner"]
    override_flag = writeback_compatibility["override_flag"]
    override_notes = writeback_compatibility["override_notes"] or "accepted_as_recommended"

    normalized_case_pattern = (
        f"{predicted_label}->{final_label}|path={writeback_compatibility['decision_path']}"
    )
    final_disposition = f"{final_label}|owner={final_owner}"
    routing_precedent = f"{final_owner}|path={writeback_compatibility['decision_path']}"

    vendor_identifier = vendor_profile.get("vendor_id") or vendor_profile.get("vendor_name") or "vendor_unspecified"
    vendor_specific_notes = (
        f"{vendor_identifier}|scope={vendor_profile.get('profile_scope', 'reviewed_case')}"
    )

    confidence_hint = (
        f"confidence={writeback_compatibility['confidence']}|"
        f"evidence_count={len(writeback_compatibility['evidence_sources'])}"
    )

    summary = PocBReviewedCaseSummary(
        normalized_case_pattern=normalized_case_pattern,
        final_disposition=final_disposition,
        override_reason_summary=override_notes if override_flag else "accepted_as_recommended",
        routing_precedent=routing_precedent,
        vendor_specific_notes=vendor_specific_notes,
        confidence_hint=confidence_hint,
        bounded_notes=bounded_notes or ["Built from validated decision-memory input."],
    )
    return asdict(summary)


def validate_reviewed_case_summary(payload: dict) -> dict:
    """Validate the bounded reviewed-case summary model."""
    missing_fields = [field_name for field_name in REVIEWED_CASE_SUMMARY_REQUIRED_FIELDS if field_name not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Reviewed-case summary is missing required field(s): {missing}.")

    for string_field in REVIEWED_CASE_SUMMARY_REQUIRED_FIELDS + (
        "summary_kind",
        "retrieval_friendly_semantics",
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

    forbidden_fragments = ("chain-of-thought", "raw_response", "output_text", "prompt", "provider")
    for field_name in REVIEWED_CASE_SUMMARY_REQUIRED_FIELDS:
        lower_value = payload[field_name].lower()
        if any(fragment in lower_value for fragment in forbidden_fragments):
            raise ValueError(f"Field '{field_name}' contains disallowed verbose or unsafe content.")

    return payload
