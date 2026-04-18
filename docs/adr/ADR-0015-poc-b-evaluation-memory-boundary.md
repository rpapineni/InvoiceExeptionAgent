# ADR-0015: PoC B Evaluation Memory Boundary

## Status

Accepted

## Context

PoC A-F provides a bounded first-pass triage foundation. PoC B extends that workflow into a learning-oriented system that must also prove measurable improvement over time. Evaluation memory is the bounded layer for benchmark, repeated-pattern, replay, regression, and failure-classification artifacts.

This note and the associated schema define the bounded evaluation-memory boundary only. This story does not implement replay execution, learning-metric aggregation, retrieval behavior, reviewer writeback orchestration, or autonomous workflow behavior.

## Decision

The PoC B evaluation-memory boundary represents structured evaluation artifacts used to measure, replay, regress, and classify learning-oriented system behavior over time. It is not current-run session continuity, not retrieval-oriented knowledge context, not reviewed-outcome truth storage, and not generic chat history.

### Required bounded contents

At minimum, bounded evaluation memory supports:

- `benchmark_case_set` for structured benchmark comparison assets
- `repeated_pattern_case_set` for repeated-pattern evaluation assets
- `replay_cases` for replay-from-correction artifacts
- `regression_history` for tracked regression records
- `failure_taxonomy` for structured failure classification artifacts

### Evaluation-oriented principle

Evaluation memory is designed for:

- benchmark comparison
- repeated-pattern evaluation
- replay-from-correction artifacts
- regression tracking
- failure classification

It is not runtime decisioning state or reusable business-context retrieval.

### Separation principle

Evaluation memory is distinct from:

- session memory for in-flight run continuity
- knowledge memory for retrieval-oriented business context
- decision memory for reviewed outcomes, override history, vendor exception profiles, routing tendencies, confidence history, and remediation patterns

### Structured and queryable principle

Evaluation memory is intended to store structured and queryable evaluation artifacts, not freeform notes or generic history capture.

### Boundedness principle

Evaluation memory remains bounded and implementation-safe. It does not:

- silently become replay execution logic
- silently become learning-metric aggregation logic
- expose chain-of-thought or hidden reasoning
- imply retrieval behavior is already implemented
- imply reviewer writeback orchestration is already implemented

## Consequences

- PoC B has a clear structured and queryable evaluation-memory layer for benchmark, replay, regression, and failure-classification assets.
- Later stories can implement replay execution or learning-metric aggregation against a stable bounded evaluation-memory contract.
