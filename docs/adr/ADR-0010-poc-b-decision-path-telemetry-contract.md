# ADR-0010: PoC B Decision-Path Telemetry Contract

## Status

Accepted

## Context

PoC A-F already established a bounded first-pass triage workflow with audit-friendly metadata and trace behavior. PoC B extends this into a learning-oriented system, which means it must also observe how a case was handled across its documented decision ladder.

This telemetry contract defines the bounded run-level telemetry needed to observe which PoC B decision path was used and how a case moved across lighter and heavier handling paths. This note and the associated schema define the telemetry contract only. They do not implement bounded trace stages, retrieval, replay, memory, reviewer writeback persistence, learning-metric aggregation, or autonomous workflow behavior.

## Decision

The PoC B decision-path telemetry contract represents the bounded run-level telemetry needed to observe which decision path was used, how escalation occurred, and how human-review posture and bounded usage reporting were preserved.

### Required telemetry fields

At minimum, the contract includes:

- `selected_path`
- `path_transitions`
- `escalation_reason`
- `retry_count`
- `latency_ms`
- `human_review_required`
- `usage_summary`

Optional bounded companion fields may also be present when helpful and still bounded, such as:

- `engine_mode`
- `path_confidence_source`
- `decision_path_version`

### Path compatibility

The telemetry contract supports all documented PoC B decision-ladder paths:

- `deterministic`
- `retrieval_assisted`
- `full_reasoning`
- `hybrid`

### Bounded usage principle

Usage is captured in bounded summary form only. The telemetry contract does not require verbose reasoning logs, chain-of-thought capture, or raw provider-internals storage.

### Human-review principle

The telemetry contract explicitly supports indicating that human review was required or involved, consistent with PoC B’s human-in-the-loop pilot posture.

## Consequences

- PoC B has a formal telemetry contract and schema for path-level observability that is consistent with current project patterns.
- Later stories can implement richer path-level observability or reporting against this bounded contract without changing the meaning of the core telemetry fields.
- Human review and bounded usage posture remain explicit because the contract stays structured, concise, and audit-friendly.
