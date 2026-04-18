# ADR-0013: PoC B Knowledge Memory Boundary

## Status

Accepted

## Context

PoC A-F established a bounded first-pass triage workflow. PoC B extends that workflow into a learning-oriented system and requires multiple distinct memory layers. After session memory, the next bounded layer is knowledge memory for retrieval-oriented business context that may inform future handling.

This note and the associated schema define the bounded knowledge-memory boundary only. This story does not implement decision memory, evaluation memory, retrieval behavior, replay, reviewer writeback persistence, long-term learning metrics, or autonomous workflow behavior.

## Decision

The PoC B knowledge-memory boundary represents retrieval-oriented business context that may inform future handling. It is not current-run session continuity, not reviewed-outcome truth, not replay or regression memory, and not generic chat history.

### Required bounded contents

At minimum, bounded knowledge memory supports:

- `policies` for concise policy objects that can later be retrieved as business context
- `sops` for concise standard-operating-procedure objects
- `playbooks` for bounded playbook guidance objects
- `routing_guidance` for reusable routing-oriented business context
- `reviewed_case_summaries` for retrieval-friendly reviewed case summaries rather than full reviewed truth records

### Retrieval-oriented principle

Knowledge memory is designed for retrieval-friendly business context:

- concise and reusable knowledge objects
- not raw hidden reasoning
- not raw prompt or provider dumps
- not generic conversation accumulation

### Separation principle

Knowledge memory is distinct from:

- session memory for in-flight run continuity
- decision memory for reviewed outcomes, final labels and owners, override history, vendor exception profiles, routing tendencies, confidence history, and remediation patterns
- evaluation memory for benchmark sets, replay cases, regression history, and failure taxonomy

### Boundedness principle

Knowledge memory remains bounded and implementation-safe. It does not:

- silently become decision or outcome truth storage
- silently become replay or evaluation storage
- expose chain-of-thought or hidden reasoning
- imply similar-case retrieval is already implemented

## Consequences

- PoC B has a clear retrieval-oriented knowledge-memory layer that remains separate from session continuity and reviewed-outcome truth.
- Later stories can implement decision memory, evaluation memory, or retrieval behavior against a stable bounded knowledge-memory contract.
