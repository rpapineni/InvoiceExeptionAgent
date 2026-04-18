"""Bounded reviewed-outcome persistence helpers for PoC B decision memory."""

from __future__ import annotations

from invoice_exception_poc_a.memory.decision import build_decision_memory, validate_decision_memory
from invoice_exception_poc_a.review.feedback import validate_reviewer_feedback
from invoice_exception_poc_a.memory.writeback import (
    REVIEWED_OUTCOME_PERSISTENCE_REQUIRED_SIGNALS,
    validate_reviewed_case_writeback,
)


def persist_reviewed_outcome_to_decision_memory(
    *,
    triage_output: dict,
    reviewer_feedback: dict,
    writeback_signals: dict,
    vendor_exception_profile: dict | None = None,
    routing_tendencies: list[dict] | None = None,
    confidence_history: list[dict] | None = None,
    remediation_patterns: list[dict] | None = None,
    bounded_notes: list[str] | None = None,
) -> dict:
    """Convert a reviewed case outcome into a valid decision-memory record."""
    reviewer_feedback = validate_reviewer_feedback(reviewer_feedback)
    validated_writeback = validate_reviewed_case_writeback(
        triage_output=triage_output,
        reviewer_feedback=reviewer_feedback,
        writeback_signals=writeback_signals,
    )

    required_triage_fields = ("case_id", "exception_type", "recommended_owner", "confidence")
    missing_triage_fields = [field_name for field_name in required_triage_fields if field_name not in triage_output]
    if missing_triage_fields:
        missing = ", ".join(missing_triage_fields)
        raise ValueError(f"Reviewed-outcome persistence is missing triage field(s): {missing}.")

    missing_signals = [
        field_name for field_name in REVIEWED_OUTCOME_PERSISTENCE_REQUIRED_SIGNALS if field_name not in writeback_signals
    ]
    if missing_signals:
        missing = ", ".join(missing_signals)
        raise ValueError(f"Reviewed-outcome persistence is missing writeback signal(s): {missing}.")

    predicted_label = triage_output["exception_type"]
    predicted_owner = triage_output["recommended_owner"]
    final_label = reviewer_feedback["final_label"]
    final_owner = reviewer_feedback["final_owner"]
    override_flag = reviewer_feedback["override_flag"]

    reviewed_outcome = {
        "case_id": triage_output["case_id"],
        "predicted_label": predicted_label,
        "predicted_owner": predicted_owner,
        "final_label": final_label,
        "final_owner": final_owner,
        "accept_as_is": reviewer_feedback["accept_as_is"],
        "reviewer_notes": reviewer_feedback["reviewer_notes"],
        "ambiguous_or_novel_flag": reviewer_feedback["ambiguous_or_novel_flag"],
        "precedent_usefulness_flag": reviewer_feedback["precedent_usefulness_flag"],
        "review_action": reviewer_feedback.get("review_action", "review_completed"),
    }

    override_history = [
        {
            "override_flag": override_flag,
            "override_label": reviewer_feedback.get("override_label"),
            "override_owner": reviewer_feedback.get("override_owner"),
            "override_notes": reviewer_feedback.get("override_notes", ""),
        }
    ]

    writeback_compatibility = {
        "predicted_label": validated_writeback["predicted_label"],
        "predicted_owner": validated_writeback["predicted_owner"],
        "override_flag": validated_writeback["override_flag"],
        "override_notes": validated_writeback["override_notes"],
        "decision_path": validated_writeback["decision_path"],
        "evidence_sources": validated_writeback["evidence_sources"],
        "rule_hits": validated_writeback["rule_hits"],
        "similar_case_refs": validated_writeback["similar_case_refs"],
        "confidence": validated_writeback["confidence"],
        "usage_summary": validated_writeback["usage_summary"],
    }

    decision_memory = build_decision_memory(
        reviewed_outcome=reviewed_outcome,
        final_label=final_label,
        final_owner=final_owner,
        override_history=override_history,
        vendor_exception_profile=vendor_exception_profile
        or {
            "source_case_id": triage_output["case_id"],
            "profile_scope": "reviewed_outcome_persistence",
            "final_owner": final_owner,
        },
        routing_tendencies=routing_tendencies
        or [
            {
                "owner": final_owner,
                "source_case_id": triage_output["case_id"],
                "review_action": reviewer_feedback.get("review_action", "review_completed"),
            }
        ],
        confidence_history=confidence_history
        or [
            {
                "confidence": triage_output["confidence"],
                "source": "first_pass_prediction",
            }
        ],
        remediation_patterns=remediation_patterns
        or [
            {
                "pattern": final_label,
                "source_case_id": triage_output["case_id"],
                "review_action": reviewer_feedback.get("review_action", "review_completed"),
            }
        ],
        writeback_compatibility=writeback_compatibility,
        bounded_notes=bounded_notes or ["Persisted from structured reviewer feedback."],
    )
    return validate_decision_memory(decision_memory)
