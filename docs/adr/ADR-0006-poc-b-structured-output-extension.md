# ADR-0006: PoC B Structured Output Extension

## Status

Accepted

## Context

PoC A-F already returns a bounded structured triage payload for one invoice exception case at a time. That structured triage contract remains the inherited baseline for PoC B and must stay comparable to the existing PoC A-F foundation.

PoC B does not replace that contract. It extends it with additional bounded metadata fields to support traceability, future reviewer writeback, and later learning-oriented capabilities. This note defines those extension fields only. It does not implement reviewer writeback, memory persistence, retrieval, replay, or autonomous workflow behavior.

## Decision

PoC B preserves the existing PoC A-F structured triage contract and extends it rather than replacing it.

The inherited PoC A-F business output fields remain required and unchanged unless a later story explicitly modifies them. The existing bounded triage recommendation output is the foundation for PoC B compatibility.

### PoC B extension fields

The PoC B structured output extension adds bounded fields or placeholders for:

- `decision_path`
- `evidence_sources`
- `confidence`
- `rule_hits`
- `similar_case_refs`

Optional bounded companion metadata may also be used later if still kept inside the pilot boundary, such as:

- `path_metadata`
- `usage_summary`
- `trace_refs`

### Field intent

- `decision_path`
  - indicates which bounded path produced the recommendation, such as deterministic, retrieval-assisted, full reasoning, or hybrid handling
- `evidence_sources`
  - identifies what source types influenced the result, such as case facts, explicit rules, reviewer outcomes, or reusable precedent context
- `confidence`
  - records recommendation confidence in a traceable way alongside the inherited structured output
- `rule_hits`
  - captures relevant explicit checks, policies, or rule-style conditions that fired during the bounded recommendation path
- `similar_case_refs`
  - provides references or placeholders for reusable precedent context in later stories without implying that similar-case reuse is already implemented here
- `path_metadata`
  - optional bounded metadata about the selected path, if later needed for observability
- `usage_summary`
  - optional bounded usage metadata for later measurement or analysis
- `trace_refs`
  - optional bounded references into traceable workflow evidence

### Boundedness principle

These fields support traceability and later learning-oriented behavior, but they do not grant autonomous authority, do not bypass human review, and do not imply that cross-case reuse is already implemented in this story.

## Explicit Non-Goals

This structured output extension does not introduce:

- reviewer writeback
- memory persistence
- retrieval behavior
- replay behavior
- business-logic changes
- decisioning changes
- validation behavior changes beyond documentation
- autonomous workflow behavior

## Consequences

- PoC A-F output comparability is preserved because the inherited structured triage contract remains the foundation.
- PoC B can later add learning-oriented traceability fields without replacing the bounded reviewer-oriented output shape.
- Reviewers can reason about later PoC B output additions as extensions to the same governed contract rather than as a new output model.
