# ADR-0009: PoC B Decision Ladder

## Status

Accepted

## Context

PoC A-F already provides a bounded first-pass triage foundation. PoC B extends that workflow into a learning-oriented system, but handling paths must remain explainable, bounded, reviewer-oriented, and traceable.

This decision ladder defines the bounded handling paths PoC B may use to produce a first-pass recommendation and learning-oriented metadata while preserving the existing control posture. This note defines the ladder only. It does not implement telemetry, bounded trace stages, retrieval, replay, memory, reviewer writeback, or runtime path selection.

## Decision

The PoC B decision ladder defines the bounded handling paths PoC B may use to produce a first-pass recommendation and learning-oriented metadata while preserving control and traceability.

### Deterministic path

The deterministic path is used when explicit business checks are sufficient to support the recommendation.

Examples include:

- tolerance thresholds
- terms mismatches
- missing PO conditions
- duplicate indicators
- vendor consistency checks

Deterministic handling remains bounded and traceable.

### Retrieval-assisted path

The retrieval-assisted path is used when relevant policy snippets, reviewed case summaries, vendor-specific patterns, or routing precedents can improve recommendation quality.

Retrieval-assisted handling remains bounded. Retrieved context is an input to recommendation quality, not autonomous authority.

### Full reasoning path

The full reasoning path is used when deterministic or retrieval-assisted handling is insufficient because the case is ambiguous, conflicting, or novel.

Full reasoning remains bounded, reviewer-oriented, and non-autonomous.

### Hybrid handling

Hybrid handling is a bounded mode where more than one path contributes to the final output.

When hybrid handling occurs, traceability must preserve what influenced the recommendation.

### Escalation semantics

At a high level, cases may move across lighter and heavier handling paths as follows:

- deterministic when the case is clear
- retrieval-assisted when precedent or policy context is helpful
- full reasoning when ambiguity, conflict, or novelty requires it

Hybrid handling may be used when multiple bounded paths contribute meaningfully to the final recommendation and the system needs to preserve path-level influence rather than hide it.

## Human-review and boundedness principles

The AP analyst remains the final decision-maker during the pilot.

The decision ladder does not authorize autonomous routing or payment action.

This story defines the ladder only. It does not implement telemetry, retrieval, bounded trace, replay, memory, reviewer writeback, or autonomous workflow behavior.

## Consequences

- PoC B has a clear and reviewable ladder of bounded handling paths.
- Later stories can implement telemetry, trace, retrieval, replay, or path-selection behavior against a stable architectural definition.
- Human review, traceability, and non-autonomous pilot boundaries remain explicit even as handling paths become more sophisticated.
