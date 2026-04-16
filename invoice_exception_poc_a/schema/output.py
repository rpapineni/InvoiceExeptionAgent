"""Formal output builder for bounded PoC A responses."""

from __future__ import annotations

from invoice_exception_poc_a.audit.logger import build_run_metadata
from invoice_exception_poc_a.audit.trace import build_trace_event
from invoice_exception_poc_a.schema.model import PocAOutput
from invoice_exception_poc_a.schema.validation import validate_output_payload


SCHEMA_VERSION = "1.0.0"


def build_placeholder_output(
    normalized_case: dict,
    triage_result: dict,
    settings,
    *,
    latency_ms: float,
    retry_count: int = 0,
    token_usage: int | None = None,
    compute_usage: str | None = None,
    execution_trace: list[dict] | None = None,
) -> dict:
    """Build the formal PoC A output payload."""
    payload = PocAOutput(
        case_id=normalized_case["case_id"],
        exception_type=triage_result["exception_type"],
        reason_summary=triage_result["reason_summary"],
        recommended_owner=triage_result["recommended_owner"],
        priority=triage_result["priority"],
        next_actions=triage_result["next_actions"],
        questions_for_reviewer=triage_result["questions_for_reviewer"],
        confidence=triage_result["confidence"],
        run_id=normalized_case["run_id"],
        workflow_version=settings.workflow_version,
        prompt_version=settings.prompt_version,
        app_env=settings.app_env,
        schema_version=SCHEMA_VERSION,
    )
    payload_dict = {
        "case_id": payload.case_id,
        "exception_type": payload.exception_type,
        "reason_summary": payload.reason_summary,
        "recommended_owner": payload.recommended_owner,
        "priority": payload.priority,
        "next_actions": payload.next_actions,
        "questions_for_reviewer": payload.questions_for_reviewer,
        "confidence": payload.confidence,
        "run_id": payload.run_id,
        "workflow_version": payload.workflow_version,
        "prompt_version": payload.prompt_version,
        "app_env": payload.app_env,
        "schema_version": payload.schema_version,
    }
    validation_result = validate_output_payload(
        payload=payload_dict,
        runtime_context={
            "run_id": normalized_case["run_id"],
            "workflow_version": settings.workflow_version,
            "prompt_version": settings.prompt_version,
            "app_env": settings.app_env,
            "schema_version": SCHEMA_VERSION,
        },
    )
    trace = list(execution_trace or [])
    schema_validation_status = "failed" if validation_result.validation_status == "failed" else "completed"
    schema_validation_note = (
        "Output matched the formal schema."
        if validation_result.validation_status == "valid"
        else "Output required one bounded repair pass."
        if validation_result.validation_status == "repaired_valid"
        else "Output failed schema validation."
    )
    trace.append(build_trace_event("schema_validation", schema_validation_status, schema_validation_note))
    trace.append(build_trace_event("output_assembly", "completed", "Assembled bounded output payload."))
    run_metadata = build_run_metadata(
        normalized_case,
        settings,
        latency_ms=latency_ms,
        retry_count=retry_count,
        validation_status=validation_result.validation_status,
        repair_count=validation_result.repair_count,
        token_usage=token_usage,
        compute_usage=compute_usage,
    )
    return {
        **validation_result.output,
        "validation_status": validation_result.validation_status,
        "validation_errors": validation_result.validation_errors,
        "repair_attempted": validation_result.repair_attempted,
        "repair_count": validation_result.repair_count,
        "run_metadata": run_metadata,
        "execution_trace": trace,
    }
