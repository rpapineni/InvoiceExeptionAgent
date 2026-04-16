"""Per-invocation run metadata assembly for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.audit.model import RunMetadata


def build_run_metadata(
    normalized_case: dict,
    settings,
    *,
    latency_ms: float,
    retry_count: int,
    validation_status: str,
    repair_count: int,
    token_usage: int | None = None,
    compute_usage: str | None = None,
) -> dict:
    """Build a consistent per-run metadata record without persistence."""
    metadata = RunMetadata(
        case_id=normalized_case["case_id"],
        run_id=normalized_case["run_id"],
        run_started_at=normalized_case["run_started_at"],
        workflow_version=settings.workflow_version,
        prompt_version=settings.prompt_version,
        app_env=settings.app_env,
        retry_count=retry_count,
        latency_ms=round(max(latency_ms, 0.0), 3),
        token_usage=token_usage,
        compute_usage=compute_usage,
        validation_status=validation_status,
        repair_count=repair_count,
    )
    return {
        "case_id": metadata.case_id,
        "run_id": metadata.run_id,
        "run_started_at": metadata.run_started_at,
        "workflow_version": metadata.workflow_version,
        "prompt_version": metadata.prompt_version,
        "app_env": metadata.app_env,
        "retry_count": metadata.retry_count,
        "latency_ms": metadata.latency_ms,
        "token_usage": metadata.token_usage,
        "compute_usage": metadata.compute_usage,
        "validation_status": metadata.validation_status,
        "repair_count": metadata.repair_count,
    }
