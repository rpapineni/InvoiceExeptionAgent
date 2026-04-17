# PoC A-F Stakeholder Demo Script

## Opening framing

Today we are showing the same bounded invoice-exception workflow in two engine modes:

- `deterministic` is the control baseline
- `frontier` is the frontier-assisted judgment layer

What stays the same in both modes:

- same intake and normalization flow
- same output schema
- same schema validation and bounded repair behavior
- same run metadata and execution trace model
- same human-review-oriented operating model

What changes in frontier mode:

- only the bounded judgment generation step for triage fields

Do say:

- the frontier path is a bounded judgment layer inside the application
- outputs remain structured, auditable, and reviewer-oriented
- this is recommendation-only and does not perform routing, payment, posting, or memory-based learning

Do not say:

- the model is autonomously resolving invoices
- the system is making payment or approval decisions
- the frontier path replaces the deterministic control plane

## Demo flow

Recommended order:

1. `samples/sample_case.json`
2. `invoice_exception_poc_a/evaluation/dataset_pack/cases/missing_po_simple.json`
3. `invoice_exception_poc_a/evaluation/dataset_pack/cases/mixed_signal_ambiguous.json`
4. `invoice_exception_poc_a/evaluation/dataset_pack/cases/insufficient_information_edge.json`

Suggested operator pattern for each case:

1. Run deterministic mode first.
2. Run frontier mode second.
3. Compare the same structured fields, validation status, and bounded trace.

Suggested commands:

```bash
TRIAGE_ENGINE=deterministic python3 -m invoice_exception_poc_a.main --input <case_path> | python3 -m json.tool
TRIAGE_ENGINE=frontier FRONTIER_PROVIDER=openai FRONTIER_MODEL=<model> python3 -m invoice_exception_poc_a.main --input <case_path> | python3 -m json.tool
```

## Case-by-case talk track

### Case 1: Happy path / receiving mismatch

- Case ID: `CASE-POCA-001`
- Path: `samples/sample_case.json`
- Compare directly: yes
- What is being demonstrated:
  - a clean successful end-to-end run through the bounded workflow
- What to point at in the output:
  - `exception_type`
  - `reason_summary`
  - `validation_status`
  - `execution_trace`
- What the audience should notice:
  - both modes stay inside the same workflow boundary and return the same governed output shape
  - this is the easiest case for establishing trust in the control plane before moving to harder examples

### Case 2: Missing PO

- Case ID: `EVAL-MISSINGPO-001`
- Path: `invoice_exception_poc_a/evaluation/dataset_pack/cases/missing_po_simple.json`
- Compare directly: yes
- What is being demonstrated:
  - obvious exception handling with a clear unusable PO anchor
- What to point at in the output:
  - `exception_type = missing_po`
  - `recommended_owner`
  - reviewer-oriented `next_actions`
- What the audience should notice:
  - both engines should converge on the same primary label
  - this case reinforces that frontier assistance does not change the bounded workflow or add autonomous action behavior

### Case 3: Mixed-signal ambiguous

- Case ID: `EVAL-AMBIG-001`
- Path: `invoice_exception_poc_a/evaluation/dataset_pack/cases/mixed_signal_ambiguous.json`
- Compare directly: yes, this is the strongest side-by-side comparison
- What is being demonstrated:
  - ambiguity handling where more than one issue could plausibly lead the triage
- What to point at in the output:
  - `reason_summary`
  - `questions_for_reviewer`
  - `confidence`
  - trace and validation still staying bounded
- What the audience should notice:
  - this is the best case for saying “same governed workflow, potentially richer judgment”
  - if the primary emphasis differs, the important point is that the same schema, validation, and trace still govern the result

### Case 4: Insufficient information / low-data edge

- Case ID: `EVAL-LOWDATA-001`
- Path: `invoice_exception_poc_a/evaluation/dataset_pack/cases/insufficient_information_edge.json`
- Compare directly: yes
- What is being demonstrated:
  - bounded behavior when the facts are incomplete and stronger claims would be unsafe
- What to point at in the output:
  - `exception_type = insufficient_information`
  - `questions_for_reviewer`
  - cautious `confidence`
  - structured validation and trace
- What the audience should notice:
  - uncertainty is handled explicitly rather than hidden
  - both modes remain reviewer-oriented and avoid unsupported conclusions

## Comparison interpretation

Use this framing while comparing outputs:

- Same primary label, richer frontier explanation:
  - say that the frontier path may improve explanation quality while remaining in the same governed structure
- Different primary emphasis, same governed workflow:
  - say that the engines can express different judgment emphasis without changing the control plane, auditability, or human-review posture
- Bounded uncertainty handling:
  - say that both modes must remain explicit about uncertainty and stay inside the same schema and validation envelope
- Same control plane across both engines:
  - say that orchestration, validation, repair limits, metadata, and trace remain deterministic layers around both engine modes

## Closing summary

Key takeaway:

- the frontier path can improve judgment quality or ambiguity handling
- the deterministic control plane still governs the workflow
- outputs remain structured, auditable, validated, and human-review-oriented

Final boundary reminder:

- this is not autonomous workflow execution
- this does not introduce routing, ERP posting, payment approval, outbound communication, or cross-case memory
- the demo should be interpreted as bounded decision support inside the same enterprise-safe workflow
