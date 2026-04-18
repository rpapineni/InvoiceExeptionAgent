# PoC B Demo Inputs

These files are ready-to-run companion inputs for the PoC B end-to-end demo runner.

Use them with `samples/sample_case.json`:

```bash
python3 -m invoice_exception_poc_a.demo.runner \
  --input /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/sample_case.json \
  --reviewer-feedback /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/poc_b_demo/accept_as_is_reviewer_feedback.json \
  --writeback-signals /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/poc_b_demo/accept_as_is_writeback_signals.json \
  --output-dir /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/poc_b_demo/output
```

Override demo:

```bash
python3 -m invoice_exception_poc_a.demo.runner \
  --input /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/sample_case.json \
  --reviewer-feedback /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/poc_b_demo/override_reviewer_feedback.json \
  --writeback-signals /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/poc_b_demo/override_writeback_signals.json \
  --output-dir /Users/rampapineni/Documents/Codex/Invoice Exception Agent PoCA/samples/poc_b_demo/output
```
