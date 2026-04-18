"""Bounded vendor exception profile helpers for PoC B."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from invoice_exception_poc_a.memory.decision import validate_decision_memory
from invoice_exception_poc_a.memory.summary import validate_reviewed_case_summary


VENDOR_EXCEPTION_PROFILE_REQUIRED_FIELDS = (
    "vendor_ref",
    "common_exception_types",
    "routing_tendency",
    "override_tendency",
    "terms_mismatch_tendency",
    "confidence_trend",
    "remediation_tendency",
)


@dataclass(frozen=True)
class PocBVendorExceptionProfile:
    """Bounded recurring vendor-specific exception behavior for PoC B."""

    vendor_ref: str
    common_exception_types: list[str]
    routing_tendency: str
    override_tendency: str
    terms_mismatch_tendency: str
    confidence_trend: str
    remediation_tendency: str
    profile_kind: str = "vendor_exception_profile"
    reusable_pattern_semantics: str = "bounded_vendor_pattern_intelligence"
    bounded_notes: list[str] = field(default_factory=list)


def build_vendor_exception_profile(
    *,
    decision_memory: dict,
    reviewed_case_summary: dict | None = None,
    bounded_notes: list[str] | None = None,
) -> dict:
    """Build a bounded vendor exception profile from reviewed-case-compatible inputs."""
    decision_memory = validate_decision_memory(decision_memory)
    if reviewed_case_summary is not None:
        reviewed_case_summary = validate_reviewed_case_summary(reviewed_case_summary)

    reviewed_outcome = decision_memory["reviewed_outcome"]
    writeback_compatibility = decision_memory["writeback_compatibility"]
    vendor_profile = decision_memory["vendor_exception_profile"]

    vendor_ref = (
        vendor_profile.get("vendor_id")
        or vendor_profile.get("vendor_name")
        or vendor_profile.get("vendor_ref")
        or "vendor_unspecified"
    )
    predicted_label = reviewed_outcome["predicted_label"]
    final_label = reviewed_outcome["final_label"]
    common_exception_types = [predicted_label]
    if final_label != predicted_label:
        common_exception_types.append(final_label)

    routing_tendency = (
        reviewed_case_summary["routing_precedent"]
        if reviewed_case_summary is not None
        else f"{decision_memory['final_owner']}|path={writeback_compatibility['decision_path']}"
    )
    override_tendency = (
        "override_common" if writeback_compatibility["override_flag"] else "accept_as_recommended_common"
    )
    terms_mismatch_tendency = (
        "recurring_terms_mismatch" if "terms" in final_label or "terms" in predicted_label else "no_terms_mismatch_pattern"
    )
    confidence_trend = writeback_compatibility["confidence"]

    remediation_patterns = decision_memory["remediation_patterns"]
    remediation_tendency = remediation_patterns[0]["pattern"] if remediation_patterns else final_label

    profile = PocBVendorExceptionProfile(
        vendor_ref=vendor_ref,
        common_exception_types=common_exception_types,
        routing_tendency=routing_tendency,
        override_tendency=override_tendency,
        terms_mismatch_tendency=terms_mismatch_tendency,
        confidence_trend=confidence_trend,
        remediation_tendency=remediation_tendency,
        bounded_notes=bounded_notes or ["Built from validated reviewed-outcome intelligence."],
    )
    return asdict(profile)


def validate_vendor_exception_profile(payload: dict) -> dict:
    """Validate the bounded vendor exception profile model."""
    missing_fields = [
        field_name for field_name in VENDOR_EXCEPTION_PROFILE_REQUIRED_FIELDS if field_name not in payload
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Vendor exception profile is missing required field(s): {missing}.")

    for string_field in (
        "vendor_ref",
        "routing_tendency",
        "override_tendency",
        "terms_mismatch_tendency",
        "confidence_trend",
        "remediation_tendency",
        "profile_kind",
        "reusable_pattern_semantics",
    ):
        if string_field in payload:
            value = payload[string_field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Field '{string_field}' must be a non-empty string.")

    common_exception_types = payload["common_exception_types"]
    if not isinstance(common_exception_types, list) or not common_exception_types:
        raise ValueError("Field 'common_exception_types' must be a non-empty list.")
    if any(not isinstance(item, str) or not item.strip() for item in common_exception_types):
        raise ValueError("Field 'common_exception_types' must contain only non-empty strings.")

    if "bounded_notes" in payload:
        bounded_notes = payload["bounded_notes"]
        if not isinstance(bounded_notes, list) or any(
            not isinstance(note, str) or not note.strip() for note in bounded_notes
        ):
            raise ValueError("Field 'bounded_notes' must be a list of non-empty strings.")

    forbidden_fragments = ("chain-of-thought", "raw_response", "output_text", "prompt", "provider", "trace dump")
    for field_name in (
        "routing_tendency",
        "override_tendency",
        "terms_mismatch_tendency",
        "confidence_trend",
        "remediation_tendency",
    ):
        lower_value = payload[field_name].lower()
        if any(fragment in lower_value for fragment in forbidden_fragments):
            raise ValueError(f"Field '{field_name}' contains disallowed verbose or unsafe content.")

    return payload
