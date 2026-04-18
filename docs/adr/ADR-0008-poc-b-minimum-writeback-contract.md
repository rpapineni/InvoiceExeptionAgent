# ADR-0008: PoC B Minimum Writeback Contract Per Reviewed Case

## Status

Accepted

## Context

PoC A-F already produces a bounded first-pass triage recommendation. PoC B must make each reviewed case contribute reusable value for future handling, not just a one-time recommendation.

This minimum writeback contract defines the least structured information every reviewed case must contribute so human-reviewed outcomes become structured, queryable, reusable workflow intelligence. This note defines the contract only. It does not implement persistence, decision memory, retrieval, replay, learning metrics, or autonomous workflow behavior.

## Decision

The minimum writeback contract defines the minimum structured information that every reviewed case must contribute so human-reviewed outcomes become reusable workflow intelligence.

### Minimum required writeback fields

Reviewed truth and calibration:

- `predicted_label`
- `final_label`

Routing improvement:

- `predicted_owner`
- `final_owner`

Override rationale:

- `override_flag`
- `override_notes`

Decision traceability:

- `decision_path`
- `evidence_sources`

Reusable handling signals:

- `rule_hits`
- `similar_case_refs`

Quality, cost, and calibration support:

- `confidence`
- `usage_summary`

### Field provenance

System first-pass triage output contributes:

- `predicted_label`
- `predicted_owner`
- `decision_path`
- `evidence_sources`
- `rule_hits`
- `similar_case_refs`
- `confidence`

Reviewer-finalized outcome contributes:

- `final_label`
- `final_owner`
- `override_flag`
- `override_notes`

Run and bounded usage context contributes:

- `usage_summary`

### Field purpose

- `predicted_label` and `final_label`
  - support calibration and reviewed-truth comparison
- `predicted_owner` and `final_owner`
  - support routing improvement and reviewer-corrected ownership learning
- `override_flag` and `override_notes`
  - support override learning and explanation of why the first-pass output changed
- `decision_path` and `evidence_sources`
  - support path traceability and interpretation of how the recommendation was formed
- `rule_hits` and `similar_case_refs`
  - support repeated-pattern handling and reusable precedent context
- `confidence` and `usage_summary`
  - support quality, cost, and calibration analysis

### Structured and queryable principle

This minimum writeback contract is intended for structured and queryable reusable workflow intelligence, not generic chat-history capture.

### Boundedness principle

This story defines the writeback contract only. It does not implement persistence yet, does not implement decision memory yet, does not implement retrieval or replay yet, does not implement learning metrics yet, does not create autonomous downstream action, and does not bypass human review.

## Consequences

- Every reviewed case has a clear minimum structured payload for future reusable workflow intelligence.
- Later PoC B stories can implement storage and reuse against the same bounded contract instead of inventing ad hoc reviewed-case history.
- Human review remains the governing control point because writeback records reviewed outcomes rather than creating autonomous handling.
