"""Bounded execution trace helpers for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.audit.model import ExecutionTraceEvent
from invoice_exception_poc_a.telemetry import ALLOWED_DECISION_PATHS


POC_B_TRACE_STAGES = (
    "triage_start",
    "decision_path_selection",
    "decision_path_telemetry_capture",
    "reviewer_outcome_pending",
    "memory_writeback_pending",
)


def build_trace_event(stage: str, status: str, note: str | None = None) -> dict:
    """Create a concise structured trace event."""
    event = ExecutionTraceEvent(stage=stage, status=status, note=note)
    return {
        "stage": event.stage,
        "status": event.status,
        "note": event.note,
    }


def build_poc_b_trace_sequence(
    *,
    selected_path: str,
    human_review_required: bool,
    failure_stage: str | None = None,
    failure_note: str | None = None,
) -> list[dict]:
    """Create a bounded PoC B stage-level trace sequence."""
    if selected_path not in ALLOWED_DECISION_PATHS:
        allowed = ", ".join(ALLOWED_DECISION_PATHS)
        raise ValueError(f"PoC B trace selected_path must be one of: {allowed}.")
    if failure_stage is not None and failure_stage not in POC_B_TRACE_STAGES:
        allowed = ", ".join(POC_B_TRACE_STAGES)
        raise ValueError(f"PoC B trace failure_stage must be one of: {allowed}.")

    stage_notes = {
        "triage_start": "Started bounded PoC B handling flow.",
        "decision_path_selection": f"Selected decision path '{selected_path}'.",
        "decision_path_telemetry_capture": "Captured bounded decision-path telemetry.",
        "reviewer_outcome_pending": (
            "Human review remains required before final reviewed truth is recorded."
            if human_review_required
            else "Reviewed outcome handoff is recorded without bypassing human control."
        ),
        "memory_writeback_pending": "Structured writeback is pending; persistence is not implemented in this story.",
    }

    trace: list[dict] = []
    for stage in POC_B_TRACE_STAGES:
        if failure_stage == stage:
            trace.append(build_trace_event(stage, "failed", failure_note or stage_notes[stage]))
            break
        trace.append(build_trace_event(stage, "completed", stage_notes[stage]))
    return trace
