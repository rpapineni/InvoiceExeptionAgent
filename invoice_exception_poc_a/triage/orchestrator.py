"""Placeholder triage orchestration for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.audit.trace import build_trace_event
from invoice_exception_poc_a.guardrails.policy import get_guardrails_snapshot
from invoice_exception_poc_a.triage.classifier import classify_primary_exception
from invoice_exception_poc_a.triage.guidance import generate_reviewer_guidance
from invoice_exception_poc_a.triage.recommender import recommend_owner_and_priority
from invoice_exception_poc_a.triage.reasoning import generate_reason_summary

def run_triage(normalized_case: dict, settings, execution_trace: list[dict] | None = None) -> dict:
    """Produce a bounded first-pass classification without downstream action."""
    trace = execution_trace if execution_trace is not None else []
    guardrails = get_guardrails_snapshot()
    classification = classify_primary_exception(normalized_case)
    trace.append(
        build_trace_event(
            "classification",
            "completed",
            f"Selected exception type '{classification['exception_type']}'.",
        )
    )
    reason_summary = generate_reason_summary(classification, normalized_case)
    trace.append(build_trace_event("reason_summary", "completed", "Generated business-readable summary."))
    recommendation = recommend_owner_and_priority(classification, normalized_case)
    trace.append(
        build_trace_event(
            "recommendation",
            "completed",
            f"Recommended owner '{recommendation['recommended_owner']}' with priority '{recommendation['priority']}'.",
        )
    )
    guidance = generate_reviewer_guidance(classification, normalized_case, recommendation)
    trace.append(
        build_trace_event(
            "guidance",
            "completed",
            f"Prepared {len(guidance['next_actions'])} actions and {len(guidance['questions_for_reviewer'])} questions.",
        )
    )
    return {
        "workflow_version": settings.workflow_version,
        "prompt_version": settings.prompt_version,
        "status": "placeholder_review_required",
        "case_id": normalized_case["case_id"],
        "exception_type": classification["exception_type"],
        "confidence": classification["confidence"],
        "reason_summary": reason_summary,
        "recommended_owner": recommendation["recommended_owner"],
        "priority": recommendation["priority"],
        "next_actions": guidance["next_actions"],
        "questions_for_reviewer": guidance["questions_for_reviewer"],
        "precedence_order": classification["precedence_order"],
        "guardrails": {
            "stateless_across_cases": guardrails["stateless_across_cases"],
            "unsupported_capabilities": guardrails["unsupported_capabilities"],
        },
        "execution_trace": trace,
    }
