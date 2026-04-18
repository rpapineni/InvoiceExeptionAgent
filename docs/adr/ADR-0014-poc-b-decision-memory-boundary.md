# ADR-0014: PoC B Decision Memory Boundary

## Status

Accepted

## Context

PoC A-F provides a bounded first-pass triage recommendation. PoC B extends that workflow into a learning-oriented system where each reviewed case must create reusable value for future handling. Decision memory is the bounded layer for reviewed-outcome truth and reusable workflow intelligence.

This note and the associated schema define the bounded decision-memory boundary only. This story does not implement evaluation memory, retrieval behavior, replay, full reviewer writeback orchestration, learning metrics, or autonomous workflow behavior.

## Decision

The PoC B decision-memory boundary represents reviewed-outcome truth and reusable workflow intelligence that may improve future handling. It is not current-run session continuity, not retrieval-oriented policy or SOP knowledge, not replay or regression storage, and not generic chat history.

### Required bounded contents

At minimum, bounded decision memory supports:

- `reviewed_outcome` for structured reviewed truth
- `final_label` for the reviewer-finalized outcome label
- `final_owner` for the reviewer-finalized owner
- `override_history` for bounded override tracking over reviewed handling
- `vendor_exception_profile` for reusable vendor-pattern context derived from reviewed outcomes
- `routing_tendencies` for structured routing-pattern intelligence
- `confidence_history` for bounded confidence-calibration history
- `remediation_patterns` for reusable remediation pattern summaries

### Minimum writeback compatibility

Decision memory remains compatible with the minimum reviewed-case writeback signals needed for reusable workflow intelligence, including:

- predicted versus final label
- predicted versus final owner
- override flag and notes
- decision path and evidence
- rule hits and similar-case references
- confidence and usage summary

These signals are accommodated as structured writeback-compatibility fields, but this story does not implement the writeback flow itself.

### Structured and queryable principle

Decision memory is intended for structured and queryable reusable workflow intelligence, not generic history capture.

### Separation principle

Decision memory is distinct from:

- session memory for in-flight run continuity
- knowledge memory for retrieval-oriented business context
- evaluation memory for benchmark sets, replay cases, regression history, and failure taxonomy

### Boundedness principle

Decision memory remains bounded and implementation-safe. It does not:

- silently become evaluation-memory storage
- silently become generic knowledge-memory retrieval storage
- expose chain-of-thought or hidden reasoning
- imply similar-case retrieval is already implemented
- imply replay is already implemented

## Consequences

- PoC B has a clear structured and queryable decision-memory layer for reviewed truth and reusable handling intelligence.
- Later stories can implement writeback flow, retrieval behavior, or evaluation capabilities against a stable bounded decision-memory contract.
