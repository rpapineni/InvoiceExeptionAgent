# ADR-0018: PoC B Writeback Validation and Auditability

## Status

Accepted

## Context

PoC B now has a reviewer outcome contract, minimum writeback contract, decision-memory schema, reviewer feedback capture flow, and reviewed-outcome persistence into decision memory. The next bounded step is to ensure reviewed-case writeback is complete, valid, and auditable before it is accepted as reusable workflow intelligence.

This note and the associated validator define the bounded writeback validation and auditability seam only. This story does not implement retrieval behavior, replay execution, learning-metric aggregation, evaluation orchestration, or autonomous workflow behavior.

## Decision

The writeback validation and auditability seam ensures that reviewed-case writeback is complete and structurally valid before it is treated as reusable workflow intelligence.

### Required validation coverage

At minimum, validation checks bounded reviewed-case writeback signals for:

- predicted label
- final label
- predicted owner
- final owner
- override flag
- override notes where applicable
- decision path
- evidence sources
- rule hits
- similar-case refs
- confidence
- usage summary

### Conditional validation behavior

The validator applies bounded conditional rules where applicable:

- if `override_flag` is true, override details must be structurally present
- required writeback-compatible fields must not be silently omitted
- malformed structured sections fail clearly

### Auditability principle

Validation failures are surfaced in a bounded, auditable way through explicit failure signals and clear failure reasons. Invalid reviewed-case writeback is not silently dropped and does not silently fall back to incomplete reusable memory.

### Compatibility principle

The validation seam remains compatible with:

- reviewer feedback capture
- reviewed-outcome persistence
- decision-memory schema

## Consequences

- PoC B protects reusable workflow intelligence from incomplete or malformed reviewed-case writeback.
- Later stories can build retrieval or broader learning behavior on top of a cleaner, auditable writeback acceptance boundary.
