# ADR-0007: PoC B Reviewer Outcome Contract

## Status

Accepted

## Context

PoC A-F already produces a bounded first-pass triage recommendation for human review. PoC B now needs a formal way to represent what happens after that recommendation is reviewed by the AP analyst so reviewed truth can later support reusable workflow intelligence.

This reviewer outcome contract defines the structured result of human review after first-pass triage. It does not implement persistence, decision memory, knowledge memory, retrieval, replay, or autonomous workflow behavior.

## Decision

The PoC B reviewer outcome contract captures the structured result of human review after first-pass triage so reviewed truth can later support reusable workflow intelligence.

### Prediction-versus-final fields

The contract clearly distinguishes what the system predicted from what the reviewer finalized. At minimum, it includes:

- `predicted_label`
- `final_label`
- `predicted_owner`
- `final_owner`

### Override fields

The contract includes:

- `override_flag`
- `override_notes`

Override semantics:

- an override is present when the reviewer changes the predicted label, predicted owner, or both
- `override_notes` explains why the reviewer changed the output
- no override does not imply autonomy or auto-resolution; it only means the reviewer accepted the first-pass recommendation

### Reviewer notes and disposition fields

The contract includes:

- `reviewer_notes`
- `final_disposition`

Optional bounded reviewer outcome metadata may also be added later if still consistent with the pilot boundary, such as:

- `review_timestamp`
- `reviewer_id`
- `review_session_ref`
- `novel_pattern_flag`
- `precedent_usefulness_flag`

### Human control principle

The AP analyst remains the final decision-maker during the pilot. This contract records reviewed truth after human review; it does not replace human judgment.

### Boundedness principle

This story defines the reviewer outcome contract only. It does not implement persistence yet, does not implement reusable memory yet, does not implement retrieval or replay yet, and does not create autonomous downstream action.

## Consequences

- PoC B has a bounded, review-centered contract for recording human-reviewed truth after first-pass triage.
- Later PoC B stories can build reusable learning behavior around the same structured reviewed outcome shape without changing the meaning of human finalization.
- Human control remains explicit because the contract records reviewed outcomes rather than automating final handling.
