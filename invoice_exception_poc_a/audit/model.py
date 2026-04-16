"""Formal run metadata structures for PoC A."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunMetadata:
    """Consistent per-run metadata for audit and evaluation handoff."""

    case_id: str
    run_id: str
    run_started_at: str
    workflow_version: str
    prompt_version: str
    app_env: str
    retry_count: int
    latency_ms: float
    token_usage: int | None
    compute_usage: str | None
    validation_status: str
    repair_count: int


@dataclass(frozen=True)
class ExecutionTraceEvent:
    """Bounded stage-level execution evidence for one run."""

    stage: str
    status: str
    note: str | None
