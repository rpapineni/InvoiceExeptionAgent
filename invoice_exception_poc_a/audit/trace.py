"""Bounded execution trace helpers for PoC A."""

from __future__ import annotations

from invoice_exception_poc_a.audit.model import ExecutionTraceEvent


def build_trace_event(stage: str, status: str, note: str | None = None) -> dict:
    """Create a concise structured trace event."""
    event = ExecutionTraceEvent(stage=stage, status=status, note=note)
    return {
        "stage": event.stage,
        "status": event.status,
        "note": event.note,
    }
