# ADR-0017: PoC B Reviewed-Outcome Persistence Into Decision Memory

## Status

Accepted

## Context

PoC A-F already produces a bounded first-pass triage recommendation. PoC B extends that workflow into a learning-oriented system where each reviewed case must create reusable workflow intelligence. The reviewer outcome contract, minimum writeback contract, decision-memory schema, and reviewer feedback capture flow are already defined.

This note and the associated helper define a bounded reviewed-outcome persistence seam only. This story does not implement retrieval behavior, replay execution, learning-metric aggregation, evaluation-memory-driven workflows, or autonomous workflow behavior.

## Decision

The reviewed-outcome persistence seam converts structured reviewed human feedback and the corresponding triage context into a valid decision-memory record for later reusable workflow intelligence.

### Inputs

At minimum, the persistence flow accepts or uses bounded inputs compatible with:

- structured first-pass triage output
- structured reviewer feedback
- minimum writeback-compatible signals

### Output

The persistence flow produces a valid decision-memory record compatible with the existing PoC B decision-memory schema. It preserves:

- reviewed outcome
- final label and final owner
- override history and notes
- writeback-compatible fields
- reusable reviewed-case intelligence fields

### Predicted-versus-final preservation

The persistence flow preserves the distinction between the system prediction and the reviewer final outcome. It does not collapse predicted and final label or owner into a single value.

### Boundedness principle

This story persists reviewed outcomes into the decision-memory layer, but it does not:

- enable retrieval behavior
- enable replay execution
- enable learning-metric aggregation
- enable autonomous routing or downstream action
- expose chain-of-thought or hidden reasoning

## Consequences

- PoC B has a bounded implementation seam for converting reviewed human feedback into valid decision-memory intelligence.
- Later stories can attach persistence orchestration or retrieval behavior to the same stable conversion seam without redefining reviewed-outcome structure.
