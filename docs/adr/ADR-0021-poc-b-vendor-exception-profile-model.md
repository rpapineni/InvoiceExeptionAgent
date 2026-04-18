# ADR-0021: PoC B Vendor Exception Profile Model

## Status

Accepted

## Context

PoC B already has decision memory for reviewed outcomes, reviewed-case summaries, a similar-case retrieval contract, and support for `vendor_pattern` as a bounded retrieval artifact type. The next bounded step is to define the actual vendor exception profile structure that captures recurring vendor-specific exception tendencies in reusable form.

This note and the associated schema define the bounded vendor exception profile model only. This story does not implement live retrieval behavior, ranking or scoring, replay execution, learning-metric aggregation, or autonomous workflow behavior.

## Decision

### Vendor profile purpose

The vendor exception profile model represents recurring vendor-specific exception behavior as reusable workflow intelligence. It is not generic one-off case storage, not live retrieval behavior, not replay or evaluation logic, and not autonomous vendor-routing authority.

### Required bounded contents

At minimum, bounded vendor exception profiles support:

- `vendor_ref`
- `common_exception_types`
- `routing_tendency`
- `override_tendency`
- `terms_mismatch_tendency`
- `confidence_trend`
- `remediation_tendency`

### Compatibility principle

The vendor exception profile remains compatible with:

- decision-memory reviewed outcomes and writeback-compatible signals
- reviewed-case summaries as concise case-level context
- the similar-case retrieval contract through the bounded `vendor_pattern` artifact type

### Reusable-pattern principle

Vendor exception profiles represent bounded recurring patterns rather than raw trace dumps, raw provider payloads, or generic freeform notes.

### Boundedness principle

The vendor exception profile remains bounded and implementation-safe. It does not:

- execute live retrieval
- rank or fetch profiles
- expose chain-of-thought
- expose raw provider payloads
- become unstructured freeform history
- imply autonomous routing authority

### Human-review principle

Vendor patterns are bounded reviewer-support context only. They do not override AP analyst review and remain consistent with PoC B's human-review-centered posture.

## Consequences

- PoC B now has a stable vendor-pattern representation that later retrieval-oriented stories can reuse.
- Future retrieval or reuse work can build on a bounded vendor profile instead of inferring patterns from raw case history.
