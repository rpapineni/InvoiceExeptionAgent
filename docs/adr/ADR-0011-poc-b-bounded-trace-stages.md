# ADR-0011: PoC B Bounded Trace Stages

## Status

Accepted

## Context

PoC A-F already established a bounded execution-trace pattern that made runs auditable without exposing hidden reasoning, raw provider internals, or verbose event logs. PoC B introduces a richer decision ladder and telemetry contract, so learning-oriented handling also needs bounded stage-level trace visibility.

This note defines the bounded PoC B trace stages and their purpose. It does not implement retrieval, replay, memory writeback persistence, reviewer writeback persistence, learning-metric aggregation, or autonomous workflow behavior.

## Decision

PoC B trace stages remain compatible with the existing bounded trace structure:

- `stage`
- `status`
- `note`

At minimum, PoC B trace-stage coverage includes:

- `triage_start`
- `decision_path_selection`
- `decision_path_telemetry_capture`
- `reviewer_outcome_pending`
- `memory_writeback_pending`

PoC B trace supports both successful stage entries and bounded failed-stage entries at the relevant stage where applicable.

Trace notes remain concise, operational, and non-sensitive. PoC B trace does not expose chain-of-thought, prompt bodies, raw provider payloads, hidden reasoning, or a verbose event log.

Human-review posture remains explicit in the trace, including review-handoff visibility where reviewed human control remains required.

## Consequences

- PoC B has a bounded, auditable stage-level trace that stays compatible with the existing project trace model.
- Later stories can add richer path-level observability without breaking the concise `stage/status/note` audit pattern.
- Human-review-centered pilot boundaries remain visible without implementing retrieval, replay, persistence, or autonomy.
