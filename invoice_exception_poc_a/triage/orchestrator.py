"""Placeholder triage orchestration for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.audit.trace import build_trace_event
from invoice_exception_poc_a.frontier_adapters import (
    FrontierJudgmentRequest,
    FrontierProviderConfig,
    get_frontier_adapter,
)
from invoice_exception_poc_a.frontier_prompt import build_frontier_triage_prompt
from invoice_exception_poc_a.guardrails.policy import get_guardrails_snapshot
from invoice_exception_poc_a.schema.frontier_parser import normalize_frontier_judgment_for_validation
from invoice_exception_poc_a.triage.classifier import classify_primary_exception
from invoice_exception_poc_a.triage.guidance import generate_reviewer_guidance
from invoice_exception_poc_a.triage.recommender import recommend_owner_and_priority
from invoice_exception_poc_a.triage.reasoning import generate_reason_summary


def run_triage(
    normalized_case: dict,
    settings,
    execution_trace: list[dict] | None = None,
    frontier_adapter_override=None,
) -> dict:
    """Produce a bounded first-pass classification without downstream action."""
    trace = execution_trace if execution_trace is not None else []
    if settings.triage_engine == "deterministic":
        return _run_deterministic_triage(normalized_case, settings, trace)
    if settings.triage_engine == "frontier":
        return _run_frontier_triage(
            normalized_case,
            settings,
            trace,
            frontier_adapter_override=frontier_adapter_override,
        )
    raise ValueError(
        f"Invalid TRIAGE_ENGINE '{settings.triage_engine}'. Allowed values: deterministic, frontier."
    )


def _run_deterministic_triage(normalized_case: dict, settings, trace: list[dict]) -> dict:
    """Run the deterministic bounded triage path."""
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
        "triage_engine": settings.triage_engine,
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


def _run_frontier_triage(
    normalized_case: dict,
    settings,
    trace: list[dict],
    *,
    frontier_adapter_override=None,
) -> dict:
    """Run bounded frontier generation using the prompt contract and configured adapter."""
    guardrails = get_guardrails_snapshot()
    prompt_package = build_frontier_triage_prompt(
        normalized_case,
        uncertainty_section=normalized_case["uncertainty"],
        prompt_version=settings.prompt_version,
    )
    trace.append(
        build_trace_event(
            "frontier_prompt_build",
            "completed",
            f"Built frontier prompt contract '{prompt_package['contract_version']}'.",
        )
    )
    adapter = frontier_adapter_override or get_frontier_adapter(settings)
    request = FrontierJudgmentRequest(
        normalized_case=normalized_case,
        uncertainty_section=normalized_case["uncertainty"],
        prompt_payload=prompt_package,
        provider_config=FrontierProviderConfig(
            provider_name=settings.frontier.provider or "",
            model_name=settings.frontier.model,
            timeout_ms=settings.frontier.timeout_ms,
            max_retries=settings.frontier.max_retries,
            temperature=settings.frontier.temperature,
            max_output_tokens=settings.frontier.max_output_tokens,
            openai_api_key=settings.frontier.openai_api_key,
        ),
    )
    try:
        response = adapter.generate_judgment(request)
    except Exception as exc:
        trace.append(
            build_trace_event(
                "frontier_adapter_call",
                "failed",
                f"Frontier adapter '{settings.frontier.provider}' raised a bounded error.",
            )
        )
        raise ValueError(f"Frontier triage generation failed during adapter call: {exc}") from exc
    adapter_status = "completed" if response.status == "success" else "failed"
    trace.append(
        build_trace_event(
            "frontier_adapter_call",
            adapter_status,
            f"Frontier adapter '{response.provider_name}' returned status '{response.status}'.",
        )
    )
    if response.status != "success":
        raise ValueError(
            f"Frontier triage generation failed with provider '{response.provider_name}' status '{response.status}'."
        )
    try:
        judgment = normalize_frontier_judgment_for_validation(
            response.parsed_output,
            case_id=normalized_case["case_id"],
        )
        trace.append(
            build_trace_event(
                "frontier_output_parse",
                "completed",
                "Parsed and normalized bounded frontier judgment fields.",
            )
        )
    except ValueError:
        trace.append(
            build_trace_event(
                "frontier_output_parse",
                "failed",
                "Frontier judgment payload failed bounded field checks.",
            )
        )
        raise
    trace.append(
        build_trace_event(
            "frontier_generation",
            "completed",
            f"Generated frontier judgment with exception type '{judgment['exception_type']}'.",
        )
    )
    return {
        "workflow_version": settings.workflow_version,
        "prompt_version": settings.prompt_version,
        "status": "placeholder_review_required",
        "triage_engine": settings.triage_engine,
        "case_id": normalized_case["case_id"],
        "exception_type": judgment["exception_type"],
        "confidence": judgment["confidence"],
        "reason_summary": judgment["reason_summary"],
        "recommended_owner": judgment["recommended_owner"],
        "priority": judgment["priority"],
        "next_actions": judgment["next_actions"],
        "questions_for_reviewer": judgment["questions_for_reviewer"],
        "guardrails": {
            "stateless_across_cases": guardrails["stateless_across_cases"],
            "unsupported_capabilities": guardrails["unsupported_capabilities"],
        },
        "execution_trace": trace,
    }
