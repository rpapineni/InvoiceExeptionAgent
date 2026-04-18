"""Basic tests for the bounded PoC A scaffold."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from invoice_exception_poc_a.config.settings import (
    ALLOWED_FRONTIER_PROVIDERS,
    ALLOWED_TRIAGE_ENGINES,
    DEFAULT_FRONTIER_MAX_OUTPUT_TOKENS,
    DEFAULT_FRONTIER_MAX_RETRIES,
    DEFAULT_FRONTIER_TEMPERATURE,
    DEFAULT_FRONTIER_TIMEOUT_MS,
    get_settings,
)
from invoice_exception_poc_a.frontier_adapters import (
    FrontierAdapter,
    FrontierJudgmentRequest,
    FrontierJudgmentResponse,
    FrontierProviderConfig,
    OpenAIFrontierAdapter,
    StubFrontierAdapter,
    get_frontier_adapter,
)
from invoice_exception_poc_a.frontier_prompt import (
    FRONTIER_TRIAGE_PROMPT_VERSION,
    REQUIRED_FRONTIER_OUTPUT_FIELDS,
    build_frontier_triage_prompt,
)
from invoice_exception_poc_a.evaluation.acceptance_report import (
    POC_A_ACCEPTANCE_CRITERIA,
    create_acceptance_report_template,
)
from invoice_exception_poc_a.evaluation.dataset import load_dataset_case, load_dataset_manifest
from invoice_exception_poc_a.evaluation.comparison_runner import (
    build_comparison_record,
    build_dual_run_comparison_report,
    run_case_for_engine,
)
from invoice_exception_poc_a.evaluation.operational_metrics import create_operational_metrics_report
from invoice_exception_poc_a.evaluation.scoring import (
    BUSINESS_QUALITY_METRICS,
    create_all_score_records,
    create_score_record,
)
from invoice_exception_poc_a.audit.trace import POC_B_TRACE_STAGES, build_poc_b_trace_sequence
from invoice_exception_poc_a.guardrails.policy import (
    UNSUPPORTED_CAPABILITIES,
    ScopeGuardrailError,
    assert_capability_supported,
    get_guardrails_snapshot,
)
from invoice_exception_poc_a.intake.contract import OPTIONAL_TOP_LEVEL_FIELDS, REQUIRED_TOP_LEVEL_FIELDS
from invoice_exception_poc_a.intake.service import build_case_envelope, load_case, validate_case_payload
from invoice_exception_poc_a.memory import (
    SESSION_MEMORY_REQUIRED_FIELDS,
    build_session_memory,
    validate_session_memory,
)
from invoice_exception_poc_a.schema.frontier_parser import parse_frontier_judgment_to_poc_a_output
from invoice_exception_poc_a.schema.frontier_parser import normalize_frontier_judgment_for_validation
from invoice_exception_poc_a.schema.model import (
    ALLOWED_CONFIDENCE_VALUES,
    ALLOWED_PRIORITY_VALUES,
    ALLOWED_VALIDATION_STATUSES,
    OUTPUT_REQUIRED_FIELDS,
)
from invoice_exception_poc_a.schema.output import SCHEMA_VERSION, build_placeholder_output
from invoice_exception_poc_a.schema.validation import validate_output_payload
from invoice_exception_poc_a.telemetry import (
    ALLOWED_DECISION_PATHS,
    DECISION_PATH_TELEMETRY_REQUIRED_FIELDS,
    build_decision_path_telemetry,
    validate_decision_path_telemetry,
)
from invoice_exception_poc_a.normalization.service import normalize_case
from invoice_exception_poc_a.triage.classifier import classify_primary_exception
from invoice_exception_poc_a.triage.guidance import generate_reviewer_guidance
from invoice_exception_poc_a.triage.model import EXCEPTION_TAXONOMY, OWNER_CATEGORIES
from invoice_exception_poc_a.triage.orchestrator import run_triage
from invoice_exception_poc_a.triage.recommender import recommend_owner_and_priority
from invoice_exception_poc_a.triage.reasoning import generate_reason_summary


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CASE = ROOT / "samples" / "sample_case.json"


class PocAScaffoldTests(unittest.TestCase):
    def run_app(self, payload_path: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-m", "invoice_exception_poc_a.main", "--input", str(payload_path)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_project_runs_for_single_case(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["case_id"], "CASE-POCA-001")
        for field in OUTPUT_REQUIRED_FIELDS:
            self.assertIn(field, payload)
        self.assertIn("run_metadata", payload)
        self.assertIn("execution_trace", payload)
        self.assertEqual(payload["run_metadata"]["triage_engine"], "deterministic")

    def test_full_valid_case_matches_formal_contract(self) -> None:
        with SAMPLE_CASE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        validated = validate_case_payload(payload)
        self.assertEqual(validated["case_id"], "CASE-POCA-001")
        for field in REQUIRED_TOP_LEVEL_FIELDS:
            self.assertIn(field, validated)
        for field in OPTIONAL_TOP_LEVEL_FIELDS:
            self.assertIn(field, validated)

    def test_full_valid_case_creates_one_envelope_with_optional_sections(self) -> None:
        with SAMPLE_CASE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        envelope = build_case_envelope(validate_case_payload(payload), get_settings())
        self.assertEqual(envelope["metadata"]["case_id"], "CASE-POCA-001")
        self.assertTrue(envelope["metadata"]["run_id"])
        self.assertTrue(envelope["metadata"]["run_started_at"])
        self.assertEqual(envelope["invoice"], payload["invoice"])
        self.assertEqual(envelope["po_summary"], payload["po_summary"])
        self.assertEqual(envelope["vendor_master"], payload["vendor_master"])
        self.assertEqual(envelope["policy_rules"], payload["policy_rules"])
        self.assertEqual(envelope["receiving_summary"], payload["receiving_summary"])
        self.assertEqual(envelope["contract_reference"], payload["contract_reference"])
        self.assertEqual(envelope["prior_analyst_notes"], payload["prior_analyst_notes"])
        self.assertEqual(envelope["upstream_exception_flags"], payload["upstream_exception_flags"])

    def test_minimal_valid_case_allows_optional_sections_to_be_absent(self) -> None:
        minimal_payload = {
            "case_id": "CASE-MIN-001",
            "invoice": {
                "invoice_number": "INV-MIN-1",
                "vendor_name": "Minimal Vendor",
                "invoice_amount": 10.0,
                "currency": "USD",
                "payment_terms": "NET_15",
            },
            "po_summary": {
                "po_number": "PO-MIN-1",
                "buyer_name": "Procurement",
                "po_amount": 10.0,
                "currency": "USD",
                "line_summary": "Single line item",
            },
            "vendor_master": {
                "vendor_id": "V-MIN-1",
                "vendor_name": "Minimal Vendor",
                "payment_terms": "NET_15",
                "payment_method": "ACH",
                "vendor_status": "ACTIVE",
            },
            "policy_rules": {
                "tolerance_threshold_percent": 2.0,
                "tolerance_threshold_amount": 25.0,
                "routing_guidance": "Send to analyst review.",
                "policy_anchor_reference": "POL-MIN-1",
            },
        }
        validated = validate_case_payload(minimal_payload)
        for field in OPTIONAL_TOP_LEVEL_FIELDS:
            self.assertNotIn(field, validated)

    def test_minimal_valid_case_creates_predictable_envelope(self) -> None:
        envelope = build_case_envelope(self._valid_minimal_payload(), get_settings())
        self.assertEqual(envelope["metadata"]["case_id"], "CASE-TEST-001")
        self.assertTrue(envelope["metadata"]["run_id"])
        self.assertTrue(envelope["metadata"]["run_started_at"])
        self.assertIsNone(envelope["receiving_summary"])
        self.assertIsNone(envelope["contract_reference"])
        self.assertIsNone(envelope["prior_analyst_notes"])
        self.assertIsNone(envelope["upstream_exception_flags"])

    def test_envelope_includes_version_and_environment_metadata(self) -> None:
        settings = get_settings()
        envelope = build_case_envelope(self._valid_minimal_payload(), settings)
        self.assertEqual(envelope["metadata"]["workflow_version"], settings.workflow_version)
        self.assertEqual(envelope["metadata"]["prompt_version"], settings.prompt_version)
        self.assertEqual(envelope["metadata"]["app_env"], settings.app_env)

    def test_full_sample_normalizes_canonical_fact_sections(self) -> None:
        with SAMPLE_CASE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        normalized = normalize_case(build_case_envelope(validate_case_payload(payload), get_settings()))
        self.assertEqual(normalized["invoice_facts"]["vendor_name"], "Placeholder Supplier LLC")
        self.assertEqual(normalized["invoice_facts"]["invoice_number"], "INV-10001")
        self.assertEqual(normalized["po_facts"]["po_number"], "PO-450001")
        self.assertEqual(normalized["vendor_facts"]["vendor_id"], "V-1020")
        self.assertEqual(normalized["policy_facts"]["routing_guidance"], payload["policy_rules"]["routing_guidance"])
        self.assertEqual(normalized["invoice_facts"]["po_reference"], "PO-450001")
        self.assertEqual(normalized["invoice_facts"]["supporting_notes"], payload["prior_analyst_notes"]["note_summary"])

    def test_minimal_case_normalizes_missing_values_as_none(self) -> None:
        normalized = normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
        self.assertIsNone(normalized["invoice_facts"]["tax"])
        self.assertIsNone(normalized["invoice_facts"]["freight"])
        self.assertIsNone(normalized["invoice_facts"]["supporting_notes"])
        self.assertIsNone(normalized["receiving_summary"])
        self.assertIsNone(normalized["contract_reference"])
        self.assertIsNone(normalized["prior_analyst_notes"])
        self.assertIsNone(normalized["upstream_exception_flags"])

    def test_missing_invoice_tax_and_freight_normalize_to_none(self) -> None:
        payload = self._valid_minimal_payload()
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        self.assertIsNone(normalized["invoice_facts"]["tax"])
        self.assertIsNone(normalized["invoice_facts"]["freight"])

    def test_versioned_envelope_normalizes_correctly(self) -> None:
        settings = get_settings()
        envelope = build_case_envelope(self._valid_minimal_payload(), settings)
        normalized = normalize_case(envelope)
        self.assertEqual(normalized["workflow_version"], settings.workflow_version)
        self.assertEqual(normalized["prompt_version"], settings.prompt_version)
        self.assertEqual(normalized["app_env"], settings.app_env)

    def test_canonical_field_names_are_used_consistently(self) -> None:
        normalized = normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
        self.assertEqual(
            sorted(normalized["invoice_facts"].keys()),
            sorted(
                [
                    "vendor_name",
                    "invoice_number",
                    "invoice_amount",
                    "payment_terms",
                    "po_reference",
                    "tax",
                    "freight",
                    "supporting_notes",
                ]
            ),
        )
        self.assertEqual(
            sorted(normalized["po_facts"].keys()),
            sorted(
                [
                    "po_number",
                    "expected_vendor",
                    "approved_total",
                    "payment_terms",
                    "quantity_expectations",
                    "comparison_anchors",
                ]
            ),
        )
        self.assertEqual(
            sorted(normalized["vendor_facts"].keys()),
            sorted(
                [
                    "canonical_vendor_name",
                    "vendor_id",
                    "standard_terms",
                    "status_flags",
                    "restrictions",
                ]
            ),
        )
        self.assertEqual(
            sorted(normalized["policy_facts"].keys()),
            sorted(
                [
                    "tolerance_thresholds",
                    "routing_guidance",
                    "exception_rules",
                    "review_instructions",
                ]
            ),
        )

    def test_normalized_case_includes_structured_uncertainty_section(self) -> None:
        normalized = normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
        self.assertEqual(
            sorted(normalized["uncertainty"].keys()),
            sorted(["missing_information", "conflicting_information", "uncertainty_flags"]),
        )

    def test_missing_po_reference_is_surfaced(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["po_number"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        codes = [item["code"] for item in normalized["uncertainty"]["missing_information"]]
        self.assertIn("missing_po_reference", codes)

    def test_missing_invoice_amount_is_surfaced(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        codes = [item["code"] for item in normalized["uncertainty"]["missing_information"]]
        self.assertIn("missing_invoice_amount", codes)

    def test_missing_vendor_identity_is_surfaced(self) -> None:
        payload = self._valid_minimal_payload()
        payload["vendor_master"]["vendor_id"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        codes = [item["code"] for item in normalized["uncertainty"]["missing_information"]]
        self.assertIn("missing_vendor_identity", codes)

    def test_vendor_name_mismatch_is_surfaced(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        codes = [item["code"] for item in normalized["uncertainty"]["conflicting_information"]]
        self.assertIn("vendor_name_mismatch", codes)

    def test_payment_terms_mismatch_is_surfaced(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["payment_terms"] = "NET_10"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        codes = [item["code"] for item in normalized["uncertainty"]["conflicting_information"]]
        self.assertIn("payment_terms_conflict", codes)

    def test_invoice_amount_above_po_total_is_surfaced(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 200.0
        payload["po_summary"]["po_amount"] = 100.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        codes = [item["code"] for item in normalized["uncertainty"]["conflicting_information"]]
        self.assertIn("invoice_amount_exceeds_po_total", codes)

    def test_clean_sample_produces_predictable_uncertainty_output(self) -> None:
        with SAMPLE_CASE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        normalized = normalize_case(build_case_envelope(validate_case_payload(payload), get_settings()))
        self.assertIn("missing_information", normalized["uncertainty"])
        self.assertIn("conflicting_information", normalized["uncertainty"])
        self.assertIn("uncertainty_flags", normalized["uncertainty"])

    def test_missing_po_reference_classifies_as_missing_po(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["po_number"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "missing_po")
        self.assertIn(result["confidence"], ("high", "medium", "low"))

    def test_vendor_mismatch_classifies_as_vendor_mismatch(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "vendor_mismatch")

    def test_terms_mismatch_classifies_as_terms_mismatch(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["payment_terms"] = "NET_10"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "terms_mismatch")

    def test_amount_above_po_total_classifies_deterministically(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 160.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 25.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 20.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "amount_mismatch")

    def test_policy_threshold_breach_classifies_deterministically(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 200.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 10.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 5.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "policy_tolerance_breach")

    def test_very_low_information_classifies_as_insufficient_information(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = None
        payload["invoice"]["invoice_number"] = None
        payload["vendor_master"]["vendor_id"] = None
        payload["policy_rules"]["routing_guidance"] = None
        payload["policy_rules"]["tolerance_threshold_amount"] = None
        payload["policy_rules"]["tolerance_threshold_percent"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "insufficient_information")
        self.assertEqual(result["confidence"], "low")

    def test_multiple_triggered_conditions_follow_precedence_rule(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["po_number"] = None
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "missing_po")

    def test_duplicate_invoice_flag_classifies_as_duplicate_invoice_suspected(self) -> None:
        payload = self._valid_minimal_payload()
        payload["upstream_exception_flags"] = {
            "source_system": "OCR_PRECHECK",
            "flags": ["duplicate_invoice_suspected"],
        }
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "duplicate_invoice_suspected")

    def test_receiving_status_classifies_as_receiving_mismatch(self) -> None:
        payload = self._valid_minimal_payload()
        payload["receiving_summary"] = {
            "receipt_status": "PARTIAL_RECEIPT",
            "received_amount": 50.0,
            "receipt_reference": "RCV-1",
        }
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        result = classify_primary_exception(normalized)
        self.assertEqual(result["exception_type"], "receiving_mismatch")

    def test_clean_sample_still_returns_one_label_and_confidence(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn(payload["exception_type"], (
            "amount_mismatch",
            "missing_po",
            "vendor_mismatch",
            "terms_mismatch",
            "duplicate_invoice_suspected",
            "receiving_mismatch",
            "policy_tolerance_breach",
            "insufficient_information",
        ))
        self.assertIn(payload["confidence"], ("high", "medium", "low"))

    def test_reason_summary_is_produced_for_missing_po_case(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["po_number"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        summary = generate_reason_summary(classification, normalized)
        self.assertIn("usable PO reference", summary)
        self.assertIn("PO anchor", summary)

    def test_reason_summary_mentions_vendor_difference(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        summary = generate_reason_summary(classify_primary_exception(normalized), normalized)
        self.assertIn("Vendor One", summary)
        self.assertIn("Different Vendor", summary)

    def test_reason_summary_mentions_conflicting_terms(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["payment_terms"] = "NET_10"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        summary = generate_reason_summary(classify_primary_exception(normalized), normalized)
        self.assertIn("NET_30", summary)
        self.assertIn("NET_10", summary)

    def test_reason_summary_mentions_invoice_vs_po_amount(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 160.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 25.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 20.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        summary = generate_reason_summary(classify_primary_exception(normalized), normalized)
        self.assertIn("160.0", summary)
        self.assertIn("150.0", summary)

    def test_reason_summary_mentions_tolerance_breach(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 200.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 10.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 5.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        summary = generate_reason_summary(classify_primary_exception(normalized), normalized)
        self.assertIn("configured tolerance thresholds", summary)
        self.assertIn("amount=10.0", summary)

    def test_reason_summary_for_insufficient_information_is_cautious(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = None
        payload["invoice"]["invoice_number"] = None
        payload["vendor_master"]["vendor_id"] = None
        payload["policy_rules"]["routing_guidance"] = None
        payload["policy_rules"]["tolerance_threshold_amount"] = None
        payload["policy_rules"]["tolerance_threshold_percent"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        summary = generate_reason_summary(classify_primary_exception(normalized), normalized)
        self.assertIn("does not have enough core information", summary)
        self.assertIn("invoice number", summary)

    def test_low_confidence_reason_summary_mentions_uncertainty_cautiously(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        payload["policy_rules"]["routing_guidance"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        summary = generate_reason_summary(classification, normalized)
        self.assertIn("Confidence is limited", summary)

    def test_clean_sample_still_returns_reason_summary(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["reason_summary"])

    def test_missing_po_maps_to_expected_owner(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["po_number"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "buyer_procurement")

    def test_vendor_mismatch_maps_to_expected_owner(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "vendor_management")

    def test_receiving_mismatch_maps_to_expected_owner(self) -> None:
        payload = self._valid_minimal_payload()
        payload["receiving_summary"] = {
            "receipt_status": "PARTIAL_RECEIPT",
            "received_amount": 50.0,
            "receipt_reference": "RCV-1",
        }
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "receiving_operations")

    def test_policy_tolerance_breach_maps_to_expected_owner_and_high_priority(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 200.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 10.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 5.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "finance_controller")
        self.assertEqual(recommendation["priority"], "high")

    def test_amount_mismatch_maps_deterministically(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 160.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 25.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 20.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "ap_analyst")
        self.assertEqual(recommendation["priority"], "medium")

    def test_insufficient_information_maps_to_exception_review_queue(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = None
        payload["invoice"]["invoice_number"] = None
        payload["vendor_master"]["vendor_id"] = None
        payload["policy_rules"]["routing_guidance"] = None
        payload["policy_rules"]["tolerance_threshold_amount"] = None
        payload["policy_rules"]["tolerance_threshold_percent"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "exception_review_queue")
        self.assertEqual(recommendation["priority"], "medium")

    def test_policy_routing_guidance_influences_owner_mapping(self) -> None:
        payload = self._valid_minimal_payload()
        payload["policy_rules"]["routing_guidance"] = "Route vendor discrepancies to vendor management review."
        payload["po_summary"]["payment_terms"] = "NET_10"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        recommendation = recommend_owner_and_priority(classify_primary_exception(normalized), normalized)
        self.assertEqual(recommendation["recommended_owner"], "vendor_management")

    def test_clean_sample_returns_one_owner_and_one_priority(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn(
            payload["recommended_owner"],
            (
                "ap_analyst",
                "buyer_procurement",
                "receiving_operations",
                "vendor_management",
                "finance_controller",
                "exception_review_queue",
            ),
        )
        self.assertIn(payload["priority"], ("low", "medium", "high"))

    def test_missing_po_case_produces_guidance(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["po_number"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("valid PO" in action for action in guidance["next_actions"]))
        self.assertTrue(any("valid PO number" in question for question in guidance["questions_for_reviewer"]))

    def test_vendor_mismatch_case_produces_vendor_focused_guidance(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("supplier" in action.lower() or "vendor" in action.lower() for action in guidance["next_actions"]))
        self.assertTrue(any("approved supplier" in question for question in guidance["questions_for_reviewer"]))

    def test_terms_mismatch_case_produces_terms_guidance(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["payment_terms"] = "NET_10"
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("payment terms" in action.lower() for action in guidance["next_actions"]))
        self.assertTrue(any("terms" in question.lower() for question in guidance["questions_for_reviewer"]))

    def test_amount_mismatch_case_produces_amount_guidance(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 160.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 25.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 20.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("invoice amount" in action.lower() for action in guidance["next_actions"]))
        self.assertTrue(any("amount difference" in question.lower() for question in guidance["questions_for_reviewer"]))

    def test_policy_tolerance_breach_case_produces_policy_guidance_without_execution(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = 200.0
        payload["po_summary"]["po_amount"] = 150.0
        payload["policy_rules"]["tolerance_threshold_amount"] = 10.0
        payload["policy_rules"]["tolerance_threshold_percent"] = 5.0
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("policy thresholds" in action.lower() for action in guidance["next_actions"]))
        self.assertTrue(all("execute" not in action.lower() for action in guidance["next_actions"]))

    def test_receiving_mismatch_case_produces_receiving_guidance(self) -> None:
        payload = self._valid_minimal_payload()
        payload["receiving_summary"] = {
            "receipt_status": "PARTIAL_RECEIPT",
            "received_amount": 50.0,
            "receipt_reference": "RCV-1",
        }
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("receiving" in action.lower() or "receipt" in action.lower() for action in guidance["next_actions"]))
        self.assertTrue(any("received" in question.lower() for question in guidance["questions_for_reviewer"]))

    def test_insufficient_information_case_asks_for_missing_anchors(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = None
        payload["invoice"]["invoice_number"] = None
        payload["vendor_master"]["vendor_id"] = None
        payload["policy_rules"]["routing_guidance"] = None
        payload["policy_rules"]["tolerance_threshold_amount"] = None
        payload["policy_rules"]["tolerance_threshold_percent"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(any("core case anchors" in action.lower() for action in guidance["next_actions"]))
        self.assertTrue(any("missing" in question.lower() or "core anchors" in question.lower() for question in guidance["questions_for_reviewer"]))

    def test_ambiguous_case_includes_uncertainty_driven_questions(self) -> None:
        payload = self._valid_minimal_payload()
        payload["po_summary"]["expected_vendor"] = "Different Vendor"
        payload["policy_rules"]["routing_guidance"] = None
        normalized = normalize_case(build_case_envelope(payload, get_settings()))
        classification = classify_primary_exception(normalized)
        recommendation = recommend_owner_and_priority(classification, normalized)
        guidance = generate_reviewer_guidance(classification, normalized, recommendation)
        self.assertTrue(
            any(
                "approved supplier" in question.lower()
                or "vendor master" in question.lower()
                or "vendor identity" in question.lower()
                for question in guidance["questions_for_reviewer"]
            )
        )

    def test_clean_sample_returns_both_guidance_lists(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["next_actions"])
        self.assertTrue(payload["questions_for_reviewer"])

    def test_low_information_case_still_returns_required_output_fields(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_amount"] = None
        payload["invoice"]["invoice_number"] = None
        payload["vendor_master"]["vendor_id"] = None
        payload["policy_rules"]["routing_guidance"] = None
        payload["policy_rules"]["tolerance_threshold_amount"] = None
        payload["policy_rules"]["tolerance_threshold_percent"] = None
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle)
            temp_path = Path(handle.name)
        try:
            result = self.run_app(temp_path)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            output = json.loads(result.stdout)
            for field in OUTPUT_REQUIRED_FIELDS:
                self.assertIn(field, output)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_output_lists_and_bounded_values_have_correct_shape(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        output = json.loads(result.stdout)
        self.assertIsInstance(output["next_actions"], list)
        self.assertIsInstance(output["questions_for_reviewer"], list)
        self.assertIn(output["confidence"], ALLOWED_CONFIDENCE_VALUES)
        self.assertIn(output["priority"], ALLOWED_PRIORITY_VALUES)
        self.assertIn(output["validation_status"], ALLOWED_VALIDATION_STATUSES)

    def test_valid_sample_output_validates_as_valid(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["validation_status"], "valid")
        self.assertEqual(output["validation_errors"], [])
        self.assertFalse(output["repair_attempted"])
        self.assertEqual(output["repair_count"], 0)
        self.assertEqual(output["run_metadata"]["validation_status"], "valid")

    def test_repairable_list_shape_validates_as_repaired_valid(self) -> None:
        payload = {
            "case_id": "CASE-REPAIR-001",
            "exception_type": "missing_po",
            "reason_summary": "Invoice is missing a usable PO reference.",
            "recommended_owner": "buyer_procurement",
            "priority": "Medium",
            "next_actions": "Verify whether a valid PO exists for this invoice.",
            "questions_for_reviewer": "Is there a valid PO number for this invoice?",
            "confidence": "High",
        }
        validation = validate_output_payload(
            payload,
            runtime_context={
                "run_id": "RUN-REPAIR-001",
                "workflow_version": "0.1.0",
                "prompt_version": "placeholder-prompt-v1",
                "app_env": "local",
                "schema_version": SCHEMA_VERSION,
            },
        )
        self.assertEqual(validation.validation_status, "repaired_valid")
        self.assertEqual(validation.output["priority"], "medium")
        self.assertEqual(validation.output["confidence"], "high")
        self.assertEqual(validation.output["next_actions"], ["Verify whether a valid PO exists for this invoice."])
        self.assertEqual(
            validation.output["questions_for_reviewer"],
            ["Is there a valid PO number for this invoice?"],
        )
        self.assertTrue(validation.repair_attempted)
        self.assertEqual(validation.repair_count, 1)

    def test_invalid_priority_fails_when_not_deterministically_repairable(self) -> None:
        payload = {
            "case_id": "CASE-BAD-PRIORITY-001",
            "exception_type": "missing_po",
            "reason_summary": "Invoice is missing a usable PO reference.",
            "recommended_owner": "buyer_procurement",
            "priority": "urgent",
            "next_actions": ["Verify whether a valid PO exists for this invoice."],
            "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
            "confidence": "high",
        }
        validation = validate_output_payload(payload)
        self.assertEqual(validation.validation_status, "failed")
        self.assertIn("priority", " ".join(validation.validation_errors))

    def test_missing_reason_summary_fails_and_is_not_fabricated(self) -> None:
        payload = {
            "case_id": "CASE-MISSING-SUMMARY-001",
            "exception_type": "missing_po",
            "recommended_owner": "buyer_procurement",
            "priority": "medium",
            "next_actions": ["Verify whether a valid PO exists for this invoice."],
            "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
            "confidence": "high",
        }
        validation = validate_output_payload(payload)
        self.assertEqual(validation.validation_status, "failed")
        self.assertNotIn("reason_summary", validation.output)
        self.assertIn("Missing required field: reason_summary.", validation.validation_errors)

    def test_missing_exception_type_fails_and_is_not_fabricated(self) -> None:
        payload = {
            "case_id": "CASE-MISSING-EXCEPTION-001",
            "reason_summary": "Not enough information to classify the case.",
            "recommended_owner": "exception_review_queue",
            "priority": "medium",
            "next_actions": ["Gather core case anchors before continuing review."],
            "questions_for_reviewer": ["What key fields are still missing?"],
            "confidence": "low",
        }
        validation = validate_output_payload(payload)
        self.assertEqual(validation.validation_status, "failed")
        self.assertNotIn("exception_type", validation.output)
        self.assertIn("Missing required field: exception_type.", validation.validation_errors)

    def test_repair_count_does_not_exceed_bounded_limit(self) -> None:
        payload = {
            "case_id": "CASE-BOUND-001",
            "exception_type": "terms_mismatch",
            "reason_summary": "Invoice terms do not align to the PO terms.",
            "recommended_owner": "ap_analyst",
            "priority": "Medium",
            "next_actions": "Compare invoice terms to the PO terms.",
            "questions_for_reviewer": "Should the PO terms govern this invoice?",
            "confidence": "Low",
        }
        validation = validate_output_payload(payload)
        self.assertLessEqual(validation.repair_count, 1)

    def test_builder_surfaces_validation_state_on_live_output(self) -> None:
        settings = get_settings()
        envelope = build_case_envelope(self._valid_minimal_payload(), settings)
        normalized = normalize_case(envelope)
        triage_result = {
            "exception_type": "amount_mismatch",
            "reason_summary": "Invoice amount differs from the approved PO total.",
            "recommended_owner": "ap_analyst",
            "priority": "medium",
            "next_actions": ["Compare invoice amount to the approved PO total."],
            "questions_for_reviewer": ["Was there an approved adjustment for this amount difference?"],
            "confidence": "high",
        }
        output = build_placeholder_output(normalized, triage_result, settings, latency_ms=5.0)
        self.assertEqual(output["validation_status"], "valid")
        self.assertEqual(output["validation_errors"], [])
        self.assertFalse(output["repair_attempted"])
        self.assertEqual(output["repair_count"], 0)
        self.assertEqual(output["run_metadata"]["repair_count"], 0)

    def test_valid_sample_run_contains_hardened_run_metadata(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        output = json.loads(result.stdout)
        metadata = output["run_metadata"]
        self.assertEqual(metadata["case_id"], output["case_id"])
        self.assertEqual(metadata["run_id"], output["run_id"])
        self.assertEqual(metadata["workflow_version"], output["workflow_version"])
        self.assertEqual(metadata["prompt_version"], output["prompt_version"])
        self.assertEqual(metadata["app_env"], output["app_env"])
        self.assertEqual(metadata["triage_engine"], "deterministic")
        self.assertTrue(metadata["run_started_at"])

    def test_retry_count_is_present_and_bounded(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        metadata = json.loads(result.stdout)["run_metadata"]
        self.assertIsInstance(metadata["retry_count"], int)
        self.assertGreaterEqual(metadata["retry_count"], 0)
        self.assertEqual(metadata["retry_count"], 0)

    def test_latency_is_present_and_non_negative(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        metadata = json.loads(result.stdout)["run_metadata"]
        self.assertIsInstance(metadata["latency_ms"], (int, float))
        self.assertGreaterEqual(metadata["latency_ms"], 0)

    def test_usage_placeholders_exist_even_when_unavailable(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        metadata = json.loads(result.stdout)["run_metadata"]
        self.assertIn("token_usage", metadata)
        self.assertIn("compute_usage", metadata)
        self.assertIsNone(metadata["token_usage"])
        self.assertIsNone(metadata["compute_usage"])

    def test_validation_repair_run_still_records_metadata_correctly(self) -> None:
        settings = get_settings()
        envelope = build_case_envelope(self._valid_minimal_payload(), settings)
        normalized = normalize_case(envelope)
        triage_result = {
            "exception_type": "missing_po",
            "reason_summary": "Invoice is missing a usable PO reference.",
            "recommended_owner": "buyer_procurement",
            "priority": "Medium",
            "next_actions": "Verify whether a valid PO exists for this invoice.",
            "questions_for_reviewer": "Is there a valid PO number for this invoice?",
            "confidence": "High",
        }
        output = build_placeholder_output(normalized, triage_result, settings, latency_ms=5.0, retry_count=0)
        self.assertEqual(output["validation_status"], "repaired_valid")
        self.assertEqual(output["run_metadata"]["validation_status"], "repaired_valid")
        self.assertEqual(output["run_metadata"]["repair_count"], 1)
        self.assertEqual(output["run_metadata"]["retry_count"], 0)

    def test_valid_sample_run_includes_expected_execution_trace_stages(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        trace = json.loads(result.stdout)["execution_trace"]
        self.assertEqual(
            [entry["stage"] for entry in trace],
            [
                "triage_engine_selection",
                "intake",
                "normalization",
                "classification",
                "reason_summary",
                "recommendation",
                "guidance",
                "schema_validation",
                "output_assembly",
            ],
        )

    def test_execution_trace_entries_have_consistent_structure(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        trace = json.loads(result.stdout)["execution_trace"]
        for entry in trace:
            self.assertEqual(sorted(entry.keys()), ["note", "stage", "status"])
            self.assertIsInstance(entry["stage"], str)
            self.assertIsInstance(entry["status"], str)
            self.assertIn(entry["status"], ("completed", "failed"))
            self.assertTrue(entry["note"] is None or isinstance(entry["note"], str))

    def test_schema_validation_stage_appears_with_completed_status(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        trace = json.loads(result.stdout)["execution_trace"]
        schema_stage = next(entry for entry in trace if entry["stage"] == "schema_validation")
        self.assertEqual(schema_stage["status"], "completed")

    def test_failed_schema_validation_path_produces_useful_bounded_trace(self) -> None:
        settings = get_settings()
        envelope = build_case_envelope(self._valid_minimal_payload(), settings)
        normalized = normalize_case(envelope)
        output = build_placeholder_output(
            normalized,
            {
                "exception_type": "missing_po",
                "reason_summary": "",
                "recommended_owner": "buyer_procurement",
                "priority": "medium",
                "next_actions": ["Verify whether a valid PO exists for this invoice."],
                "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                "confidence": "high",
            },
            settings,
            latency_ms=5.0,
            execution_trace=[
                {"stage": "intake", "status": "completed", "note": "Loaded one validated case envelope."},
                {"stage": "normalization", "status": "completed", "note": "Normalized canonical case facts."},
            ],
        )
        self.assertEqual(output["validation_status"], "failed")
        schema_stage = next(entry for entry in output["execution_trace"] if entry["stage"] == "schema_validation")
        self.assertEqual(schema_stage["status"], "failed")
        self.assertIn("failed schema validation", schema_stage["note"].lower())

    def test_default_triage_engine_is_deterministic(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
        self.assertEqual(settings.triage_engine, "deterministic")
        self.assertIsNone(settings.frontier.provider)
        self.assertIsNone(settings.frontier.model)

    def test_explicit_deterministic_triage_engine_is_used(self) -> None:
        result = self.run_app(SAMPLE_CASE, {"TRIAGE_ENGINE": "deterministic"})
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["run_metadata"]["triage_engine"], "deterministic")
        selection_stage = next(
            entry for entry in output["execution_trace"] if entry["stage"] == "triage_engine_selection"
        )
        self.assertIn("deterministic", selection_stage["note"])

    def test_frontier_triage_engine_stub_is_selectable(self) -> None:
        result = self.run_app(
            SAMPLE_CASE,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "stub",
                "FRONTIER_MODEL": "stub-placeholder-v1",
            },
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["run_metadata"]["triage_engine"], "frontier")
        prompt_stage = next(entry for entry in output["execution_trace"] if entry["stage"] == "frontier_prompt_build")
        adapter_stage = next(entry for entry in output["execution_trace"] if entry["stage"] == "frontier_adapter_call")
        parse_stage = next(entry for entry in output["execution_trace"] if entry["stage"] == "frontier_output_parse")
        generation_stage = next(entry for entry in output["execution_trace"] if entry["stage"] == "frontier_generation")
        self.assertIn("prompt contract", prompt_stage["note"].lower())
        self.assertIn("stub", adapter_stage["note"].lower())
        self.assertEqual(parse_stage["status"], "completed")
        self.assertIn(output["exception_type"], generation_stage["note"])
        self.assertEqual(output["exception_type"], "insufficient_information")
        self.assertEqual(output["recommended_owner"], "exception_review_queue")
        self.assertEqual(output["priority"], "low")

    def test_invalid_triage_engine_fails_clearly(self) -> None:
        result = self.run_app(SAMPLE_CASE, {"TRIAGE_ENGINE": "invalid_engine"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid TRIAGE_ENGINE", f"{result.stdout}\n{result.stderr}")

    def test_frontier_provider_allowed_values_are_declared(self) -> None:
        self.assertEqual(ALLOWED_FRONTIER_PROVIDERS, ("openai", "stub"))

    def test_frontier_mode_with_valid_stub_config_loads_successfully(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "stub",
                "FRONTIER_MODEL": "stub-placeholder-v1",
            },
            clear=True,
        ):
            settings = get_settings()
        self.assertEqual(settings.triage_engine, "frontier")
        self.assertEqual(settings.frontier.provider, "stub")
        self.assertEqual(settings.frontier.model, "stub-placeholder-v1")

    def test_frontier_mode_with_valid_openai_config_shape_loads_successfully(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-5.4",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            settings = get_settings()
        self.assertEqual(settings.frontier.provider, "openai")
        self.assertEqual(settings.frontier.model, "gpt-5.4")
        self.assertEqual(settings.frontier.openai_api_key, "test-key")

    def test_frontier_mode_with_invalid_provider_fails_clearly(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "invalid-provider",
                "FRONTIER_MODEL": "placeholder-model",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "Invalid FRONTIER_PROVIDER"):
                get_settings()

    def test_frontier_mode_with_missing_provider_fails_clearly(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_MODEL": "placeholder-model",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "FRONTIER_PROVIDER is required"):
                get_settings()

    def test_frontier_mode_with_missing_model_fails_clearly(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "stub",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "FRONTIER_MODEL is required"):
                get_settings()

    def test_frontier_defaults_are_present_when_optional_settings_are_omitted(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "stub",
                "FRONTIER_MODEL": "stub-placeholder-v1",
            },
            clear=True,
        ):
            settings = get_settings()
        self.assertEqual(settings.frontier.timeout_ms, DEFAULT_FRONTIER_TIMEOUT_MS)
        self.assertEqual(settings.frontier.max_retries, DEFAULT_FRONTIER_MAX_RETRIES)
        self.assertEqual(settings.frontier.temperature, DEFAULT_FRONTIER_TEMPERATURE)
        self.assertEqual(settings.frontier.max_output_tokens, DEFAULT_FRONTIER_MAX_OUTPUT_TOKENS)

    def test_run_metadata_is_consistent_in_sample_output_artifact(self) -> None:
        sample_output_path = ROOT / "samples" / "sample_output.json"
        with sample_output_path.open("r", encoding="utf-8") as handle:
            output = json.load(handle)
        metadata = output["run_metadata"]
        self.assertEqual(metadata["case_id"], output["case_id"])
        self.assertEqual(metadata["run_id"], output["run_id"])
        self.assertEqual(metadata["workflow_version"], output["workflow_version"])
        self.assertEqual(metadata["prompt_version"], output["prompt_version"])
        self.assertEqual(metadata["app_env"], output["app_env"])
        self.assertIn("latency_ms", metadata)
        self.assertIn("token_usage", metadata)
        self.assertIn("compute_usage", metadata)

    def test_sample_output_file_matches_formal_schema_shape(self) -> None:
        sample_output_path = ROOT / "samples" / "sample_output.json"
        with sample_output_path.open("r", encoding="utf-8") as handle:
            output = json.load(handle)
        for field in OUTPUT_REQUIRED_FIELDS:
            self.assertIn(field, output)
        self.assertIsInstance(output["next_actions"], list)
        self.assertIsInstance(output["questions_for_reviewer"], list)
        self.assertIn(output["confidence"], ALLOWED_CONFIDENCE_VALUES)
        self.assertIn(output["priority"], ALLOWED_PRIORITY_VALUES)
        self.assertIn(output["validation_status"], ALLOWED_VALIDATION_STATUSES)
        self.assertIn("run_metadata", output)
        self.assertIn("execution_trace", output)

    def test_dataset_manifest_loads_successfully(self) -> None:
        manifest = load_dataset_manifest()
        self.assertEqual(manifest["dataset_name"], "poc_a_evaluation_dataset_pack")
        self.assertTrue(manifest["cases"])

    def test_dataset_cases_include_required_reference_fields(self) -> None:
        manifest = load_dataset_manifest()
        for entry in manifest["cases"]:
            case_data = load_dataset_case(entry["case_file"])
            self.assertEqual(case_data["case_id"], entry["case_id"])
            self.assertIn("case_description", case_data)
            self.assertIn("coverage_bucket", case_data)
            self.assertIn("coverage_notes", case_data)
            self.assertIn("expected_outcome", case_data)
            self.assertIn("primary_exception_type", case_data["expected_outcome"])
            self.assertIn("likely_owner", case_data["expected_outcome"])
            self.assertIn("input_payload", case_data)

    def test_dataset_covers_required_buckets(self) -> None:
        manifest = load_dataset_manifest()
        buckets = {entry["coverage_bucket"] for entry in manifest["cases"]}
        self.assertIn("simple_obvious", buckets)
        self.assertIn("moderately_ambiguous", buckets)
        self.assertIn("edge_low_data", buckets)

    def test_dataset_case_payloads_conform_to_input_contract_shape(self) -> None:
        manifest = load_dataset_manifest()
        for entry in manifest["cases"]:
            case_data = load_dataset_case(entry["case_file"])
            validated = validate_case_payload(case_data["input_payload"])
            self.assertEqual(validated["case_id"], entry["case_id"])

    def test_score_record_can_be_created_for_simple_case(self) -> None:
        record = create_score_record("EVAL-AMOUNT-001")
        self.assertEqual(record["case_id"], "EVAL-AMOUNT-001")
        self.assertEqual(record["coverage_bucket"], "simple_obvious")

    def test_score_record_can_be_created_for_ambiguous_case(self) -> None:
        record = create_score_record("EVAL-AMBIG-001")
        self.assertEqual(record["case_id"], "EVAL-AMBIG-001")
        self.assertEqual(record["coverage_bucket"], "moderately_ambiguous")

    def test_all_business_quality_metrics_are_present(self) -> None:
        record = create_score_record("EVAL-AMOUNT-001")
        self.assertEqual(set(record["metric_scores"].keys()), set(BUSINESS_QUALITY_METRICS))

    def test_each_metric_supports_score_plus_evidence(self) -> None:
        record = create_score_record("EVAL-AMOUNT-001")
        for metric in BUSINESS_QUALITY_METRICS:
            self.assertEqual(sorted(record["metric_scores"][metric].keys()), ["evidence", "score"])

    def test_dataset_case_ids_map_cleanly_into_score_records(self) -> None:
        manifest = load_dataset_manifest()
        records = create_all_score_records()
        self.assertEqual(
            {record["case_id"] for record in records},
            {entry["case_id"] for entry in manifest["cases"]},
        )

    def test_operational_metrics_report_can_be_created_from_outputs(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertEqual(report["total_cases"], 3)

    def test_average_latency_is_computed_correctly(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertEqual(report["average_latency_per_case"]["value"], 2.5)

    def test_average_retries_is_computed_correctly(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertEqual(report["average_retries_per_case"]["value"], 0.333)

    def test_valid_structured_output_rate_reflects_validation_statuses(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertEqual(report["valid_structured_output_rate"]["value"], 0.667)

    def test_token_or_compute_usage_field_exists_when_unavailable(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertIn("average_token_or_compute_usage_per_case", report)
        self.assertIsNone(report["average_token_or_compute_usage_per_case"]["value"])
        self.assertTrue(report["average_token_or_compute_usage_per_case"]["note"])

    def test_estimated_analyst_time_saved_field_has_note_support(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertIn("estimated_analyst_time_saved", report)
        self.assertIn("note", report["estimated_analyst_time_saved"])
        self.assertIsNone(report["estimated_analyst_time_saved"]["value"])

    def test_operational_metrics_report_includes_all_required_fields(self) -> None:
        report = create_operational_metrics_report(self._sample_operational_outputs())
        self.assertEqual(
            sorted(report.keys()),
            sorted(
                [
                    "total_cases",
                    "average_latency_per_case",
                    "average_retries_per_case",
                    "average_token_or_compute_usage_per_case",
                    "valid_structured_output_rate",
                    "estimated_analyst_time_saved",
                ]
            ),
        )

    def test_acceptance_report_template_can_be_created(self) -> None:
        report = create_acceptance_report_template("poc_a_reference_python")
        self.assertEqual(report["implementation_id"], "poc_a_reference_python")

    def test_acceptance_report_includes_all_six_required_criteria(self) -> None:
        report = create_acceptance_report_template("poc_a_reference_python")
        self.assertEqual(set(report["criteria"].keys()), set(POC_A_ACCEPTANCE_CRITERIA))

    def test_each_acceptance_criterion_supports_score_passed_and_evidence(self) -> None:
        report = create_acceptance_report_template("poc_a_reference_python")
        for criterion in POC_A_ACCEPTANCE_CRITERIA:
            self.assertEqual(
                sorted(report["criteria"][criterion].keys()),
                ["evidence", "passed", "score"],
            )

    def test_acceptance_report_can_be_keyed_by_implementation_identifier(self) -> None:
        report = create_acceptance_report_template("implementation-under-test")
        self.assertEqual(report["implementation_id"], "implementation-under-test")

    def test_sample_acceptance_report_artifact_conforms_to_structure(self) -> None:
        sample_report_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "sample_acceptance_report.json"
        with sample_report_path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertIn("implementation_id", report)
        self.assertEqual(set(report["criteria"].keys()), set(POC_A_ACCEPTANCE_CRITERIA))

    def test_submission_package_directory_exists(self) -> None:
        package_dir = ROOT / "invoice_exception_poc_a" / "submission_package"
        self.assertTrue(package_dir.is_dir())

    def test_submission_package_section_files_exist(self) -> None:
        package_dir = ROOT / "invoice_exception_poc_a" / "submission_package"
        expected_files = {
            "README.md",
            "manifest.json",
            "architecture_overview.md",
            "workflow_diagram.md",
            "assumptions_and_exclusions.md",
            "input_contract.md",
            "output_contract.md",
            "validation_and_trace_summary.md",
            "evaluation_dataset_summary.md",
            "business_quality_scoring_summary.md",
            "operational_metrics_summary.md",
            "acceptance_report_summary.md",
            "test_results_summary.md",
            "business_findings_and_limitations.md",
        }
        self.assertEqual(
            expected_files,
            {path.name for path in package_dir.iterdir() if path.is_file()},
        )

    def test_submission_package_manifest_exists_and_is_structurally_consistent(self) -> None:
        manifest_path = ROOT / "invoice_exception_poc_a" / "submission_package" / "manifest.json"
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["package_name"], "poc_a_submission_package_skeleton")
        self.assertTrue(manifest["sections"])

    def test_submission_package_manifest_covers_required_sections(self) -> None:
        manifest_path = ROOT / "invoice_exception_poc_a" / "submission_package" / "manifest.json"
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(
            {section["section_id"] for section in manifest["sections"]},
            {
                "architecture_overview",
                "workflow_diagram",
                "assumptions_and_exclusions",
                "input_contract",
                "output_contract",
                "validation_and_trace_summary",
                "evaluation_dataset_summary",
                "business_quality_scoring_summary",
                "operational_metrics_summary",
                "acceptance_report_summary",
                "test_results_summary",
                "business_findings_and_limitations",
            },
        )

    def test_frontier_branching_strategy_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0002-poc-a-frontier-branching-strategy.md"
        self.assertTrue(adr_path.is_file())

    def test_frontier_branching_strategy_docs_cover_required_rules(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (
            ROOT / "docs" / "adr" / "ADR-0002-poc-a-frontier-branching-strategy.md"
        ).read_text(encoding="utf-8")
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "release/poc-a-deterministic-baseline",
            "feature/poc-a-frontier-assisted",
            "Do not modify the baseline branch during frontier work",
            "Preserve deterministic mode even on the frontier branch",
            "Add a mode switch rather than replacing deterministic logic",
            "Treat frontier behavior as a bounded judgment layer only",
            "Frontier experiments do not flow back into baseline automatically",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_frontier_architectural_boundary_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0003-poc-a-f-architectural-boundary.md"
        self.assertTrue(adr_path.is_file())

    def test_frontier_architectural_boundary_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (
            ROOT / "docs" / "adr" / "ADR-0003-poc-a-f-architectural-boundary.md"
        ).read_text(encoding="utf-8")
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "orchestration",
            "input contract",
            "output contract",
            "schema validation",
            "bounded repair",
            "run metadata",
            "execution trace",
            "evaluation dataset",
            "scoring and reporting structures",
            "guardrails and workflow control",
            "bounded judgment generation",
            "exception classification",
            "reason summary",
            "owner recommendation",
            "priority recommendation",
            "next actions",
            "reviewer questions",
            "confidence",
            "Frontier assistance is therefore a bounded judgment layer, not autonomous workflow execution.",
            "cross-case memory",
            "reuse of prior corrections",
            "learning loops",
            "autonomous routing",
            "ERP posting",
            "payment approval or rejection",
            "outbound communications",
            "uncontrolled tool usage",
            "PoC B learning behavior",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_working_model_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0004-poc-b-working-model.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_working_model_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0004-poc-b-working-model.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "PoC A-F is the inherited baseline for PoC B",
            "PoC B extends PoC A-F rather than replacing it",
            "one-case-in / one-triage-out bounded workflow",
            "structured triage recommendation contract",
            "human-review orientation",
            "bounded execution trace",
            "validation and control boundaries",
            "non-autonomous pilot posture",
            "reviewer outcome capture",
            "reusable workflow memory",
            "similar-case and prior-pattern reuse",
            "replay and evaluation memory",
            "measurable learning evidence",
            "Implement only the active story and nothing beyond it",
            "Do not pull future scope forward",
            "Preserve PoC A-F baseline behavior unless the active story explicitly changes it",
            "Deliver PoC B one story at a time, with review between stories",
            "autonomous routing",
            "payment action",
            "ERP posting",
            "silent auto-resolution of ambiguous cases",
            "unbounded cross-case agent behavior",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_architectural_boundary_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0005-poc-b-architectural-boundary.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_architectural_boundary_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0005-poc-b-architectural-boundary.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "PoC A-F remains the bounded triage foundation",
            "PoC B is a learning-oriented layer around that foundation, not a replacement for it",
            "one-case-in / one-triage-out bounded triage flow",
            "reviewer-oriented structured recommendation contract",
            "orchestration",
            "input and output contracts",
            "validation and bounded repair behavior",
            "metadata and bounded trace posture",
            "pilot control boundaries",
            "reviewer outcome capture after triage",
            "reusable workflow memory",
            "decision memory for reviewed outcomes",
            "knowledge memory for retrieval-oriented context",
            "evaluation memory for replay and regression",
            "similar-case reuse",
            "learning-oriented observability and improvement evidence",
            "The AP analyst remains in control of the final handling decision during this pilot",
            "autonomous routing",
            "payment action",
            "ERP posting",
            "outbound financial execution",
            "silent auto-resolution of ambiguous cases",
            "unbounded cross-case agent behavior",
            "open-ended tool orchestration beyond bounded pilot scope",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_structured_output_extension_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0006-poc-b-structured-output-extension.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_structured_output_extension_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0006-poc-b-structured-output-extension.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "PoC B preserves the existing PoC A-F structured triage contract and extends it rather than replacing it",
            "The inherited PoC A-F business output fields remain required and unchanged",
            "`decision_path`",
            "`evidence_sources`",
            "`confidence`",
            "`rule_hits`",
            "`similar_case_refs`",
            "indicates which bounded path produced the recommendation",
            "identifies what source types influenced the result",
            "records recommendation confidence",
            "captures relevant explicit checks",
            "provides references or placeholders for reusable precedent context",
            "do not grant autonomous authority",
            "do not bypass human review",
            "do not imply that cross-case reuse is already implemented in this story",
            "reviewer writeback",
            "memory persistence",
            "retrieval behavior",
            "replay behavior",
            "business-logic changes",
            "autonomous workflow behavior",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_reviewer_outcome_contract_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0007-poc-b-reviewer-outcome-contract.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_reviewer_outcome_contract_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0007-poc-b-reviewer-outcome-contract.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "captures the structured result of human review after first-pass triage",
            "`predicted_label`",
            "`final_label`",
            "`predicted_owner`",
            "`final_owner`",
            "`override_flag`",
            "`override_notes`",
            "an override is present when the reviewer changes the predicted label, predicted owner, or both",
            "no override does not imply autonomy or auto-resolution",
            "`reviewer_notes`",
            "`final_disposition`",
            "The AP analyst remains the final decision-maker during the pilot",
            "does not implement persistence yet",
            "does not implement reusable memory yet",
            "does not implement retrieval or replay yet",
            "does not create autonomous downstream action",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_minimum_writeback_contract_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0008-poc-b-minimum-writeback-contract.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_minimum_writeback_contract_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0008-poc-b-minimum-writeback-contract.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "defines the minimum structured information that every reviewed case must contribute",
            "`predicted_label`",
            "`final_label`",
            "`predicted_owner`",
            "`final_owner`",
            "`override_flag`",
            "`override_notes`",
            "`decision_path`",
            "`evidence_sources`",
            "`rule_hits`",
            "`similar_case_refs`",
            "`confidence`",
            "`usage_summary`",
            "System first-pass triage output contributes",
            "Reviewer-finalized outcome contributes",
            "Run and bounded usage context contributes",
            "support calibration and reviewed-truth comparison",
            "support routing improvement",
            "support override learning",
            "support path traceability",
            "support repeated-pattern handling",
            "support quality, cost, and calibration analysis",
            "structured and queryable reusable workflow intelligence",
            "not generic chat-history capture",
            "does not implement persistence yet",
            "does not implement decision memory yet",
            "does not implement retrieval or replay yet",
            "does not implement learning metrics yet",
            "does not create autonomous downstream action",
            "does not bypass human review",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_decision_ladder_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0009-poc-b-decision-ladder.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_decision_ladder_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0009-poc-b-decision-ladder.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "defines the bounded handling paths PoC B may use",
            "### Deterministic path",
            "### Retrieval-assisted path",
            "### Full reasoning path",
            "### Hybrid handling",
            "tolerance thresholds",
            "terms mismatches",
            "missing PO conditions",
            "duplicate indicators",
            "vendor consistency checks",
            "Retrieved context is an input to recommendation quality, not autonomous authority",
            "Full reasoning remains bounded, reviewer-oriented, and non-autonomous",
            "traceability must preserve what influenced the recommendation",
            "deterministic when the case is clear",
            "retrieval-assisted when precedent or policy context is helpful",
            "full reasoning when ambiguity, conflict, or novelty requires it",
            "The AP analyst remains the final decision-maker during the pilot",
            "does not authorize autonomous routing or payment action",
            "does not implement telemetry, retrieval, bounded trace, replay, memory, reviewer writeback, or autonomous workflow behavior",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_decision_path_telemetry_contract_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0010-poc-b-decision-path-telemetry-contract.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_decision_path_telemetry_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (
            ROOT / "docs" / "adr" / "ADR-0010-poc-b-decision-path-telemetry-contract.md"
        ).read_text(encoding="utf-8")
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "observe which decision path was used",
            "`selected_path`",
            "`path_transitions`",
            "`escalation_reason`",
            "`retry_count`",
            "`latency_ms`",
            "`human_review_required`",
            "`usage_summary`",
            "`deterministic`",
            "`retrieval_assisted`",
            "`full_reasoning`",
            "`hybrid`",
            "does not require verbose reasoning logs, chain-of-thought capture, or raw provider-internals storage",
            "human review was required or involved",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_decision_path_telemetry_supports_deterministic_path(self) -> None:
        telemetry = build_decision_path_telemetry(
            selected_path="deterministic",
            path_transitions=["deterministic"],
            escalation_reason=None,
            retry_count=0,
            latency_ms=2.0,
            human_review_required=True,
            usage_summary={"token_usage": None, "compute_usage": None},
            engine_mode="deterministic",
            decision_path_version="poc-b-ladder-v1",
        )
        validated = validate_decision_path_telemetry(telemetry)
        self.assertEqual(validated["selected_path"], "deterministic")

    def test_decision_path_telemetry_supports_retrieval_assisted_path(self) -> None:
        telemetry = build_decision_path_telemetry(
            selected_path="retrieval_assisted",
            path_transitions=["deterministic", "retrieval_assisted"],
            escalation_reason="policy_context_helpful",
            retry_count=0,
            latency_ms=4.5,
            human_review_required=True,
            usage_summary={"retrieved_context_count": 2},
            engine_mode="frontier",
            path_confidence_source="retrieval_context",
        )
        validated = validate_decision_path_telemetry(telemetry)
        self.assertEqual(validated["selected_path"], "retrieval_assisted")

    def test_decision_path_telemetry_supports_full_reasoning_path(self) -> None:
        telemetry = build_decision_path_telemetry(
            selected_path="full_reasoning",
            path_transitions=["deterministic", "full_reasoning"],
            escalation_reason="ambiguous_conflicting_case",
            retry_count=0,
            latency_ms=8.0,
            human_review_required=True,
            usage_summary={"token_usage": None},
            engine_mode="frontier",
            path_confidence_source="reasoning_needed",
        )
        validated = validate_decision_path_telemetry(telemetry)
        self.assertEqual(validated["selected_path"], "full_reasoning")

    def test_decision_path_telemetry_supports_hybrid_path(self) -> None:
        telemetry = build_decision_path_telemetry(
            selected_path="hybrid",
            path_transitions=["deterministic", "retrieval_assisted", "hybrid"],
            escalation_reason="multiple_paths_contributed",
            retry_count=1,
            latency_ms=9.5,
            human_review_required=True,
            usage_summary={"token_usage": None, "retrieved_context_count": 1},
            engine_mode="frontier",
            bounded_notes=["Hybrid output preserved path influence."],
        )
        validated = validate_decision_path_telemetry(telemetry)
        self.assertEqual(validated["selected_path"], "hybrid")

    def test_decision_path_telemetry_missing_required_field_fails_clearly(self) -> None:
        payload = build_decision_path_telemetry(
            selected_path="deterministic",
            path_transitions=["deterministic"],
            escalation_reason=None,
            retry_count=0,
            latency_ms=2.0,
            human_review_required=True,
            usage_summary={"token_usage": None},
        )
        del payload["usage_summary"]
        with self.assertRaisesRegex(ValueError, "usage_summary"):
            validate_decision_path_telemetry(payload)

    def test_poc_b_bounded_trace_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0011-poc-b-bounded-trace-stages.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_bounded_trace_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0011-poc-b-bounded-trace-stages.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "`stage`",
            "`status`",
            "`note`",
            "`triage_start`",
            "`decision_path_selection`",
            "`decision_path_telemetry_capture`",
            "`reviewer_outcome_pending`",
            "`memory_writeback_pending`",
            "bounded failed-stage entries",
            "does not expose chain-of-thought",
            "raw provider internals",
            "Human-review posture remains explicit",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_poc_b_successful_trace_sequence_is_bounded_and_structured(self) -> None:
        trace = build_poc_b_trace_sequence(selected_path="hybrid", human_review_required=True)
        self.assertEqual([entry["stage"] for entry in trace], list(POC_B_TRACE_STAGES))
        for entry in trace:
            self.assertEqual(sorted(entry.keys()), ["note", "stage", "status"])
            self.assertEqual(entry["status"], "completed")
            self.assertIsInstance(entry["note"], str)
            for forbidden_marker in ("chain-of-thought", "prompt", "raw_response", "output_text"):
                self.assertNotIn(forbidden_marker, entry["note"].lower())
        review_stage = next(entry for entry in trace if entry["stage"] == "reviewer_outcome_pending")
        self.assertIn("human review", review_stage["note"].lower())

    def test_poc_b_failed_trace_stage_is_emitted_at_relevant_stage(self) -> None:
        trace = build_poc_b_trace_sequence(
            selected_path="retrieval_assisted",
            human_review_required=True,
            failure_stage="decision_path_telemetry_capture",
            failure_note="Decision-path telemetry capture failed bounded validation.",
        )
        self.assertEqual(
            [entry["stage"] for entry in trace],
            ["triage_start", "decision_path_selection", "decision_path_telemetry_capture"],
        )
        self.assertEqual(trace[-1]["status"], "failed")
        self.assertIn("telemetry capture failed", trace[-1]["note"].lower())

    def test_poc_b_session_memory_boundary_document_exists(self) -> None:
        adr_path = ROOT / "docs" / "adr" / "ADR-0012-poc-b-session-memory-boundary.md"
        self.assertTrue(adr_path.is_file())

    def test_poc_b_session_memory_docs_cover_required_boundaries(self) -> None:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_text = (ROOT / "docs" / "adr" / "ADR-0012-poc-b-session-memory-boundary.md").read_text(
            encoding="utf-8"
        )
        combined = readme_text + "\n" + adr_text
        required_markers = [
            "current in-flight run only",
            "`case_context`",
            "`tool_outputs`",
            "`active_reasoning_state`",
            "`reviewer_session_state`",
            "ephemeral",
            "cleanup or reset at the end of the run or review session",
            "knowledge memory",
            "decision memory",
            "evaluation memory",
            "not generic conversation history",
            "does not implement knowledge memory, decision memory, evaluation memory, retrieval, replay, reviewer writeback persistence, long-term storage, or autonomous workflow behavior",
            "The AP analyst remains the final decision-maker during the pilot",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

    def test_session_memory_supports_in_flight_case_context_and_tool_outputs(self) -> None:
        session_memory = build_session_memory(
            case_context={"case_id": "CASE-123", "coverage_bucket": "mixed_signal"},
            tool_outputs=[
                {"tool_name": "normalization", "status": "completed"},
                {"tool_name": "policy_lookup", "status": "completed"},
            ],
            active_reasoning_state={"selected_path": "deterministic", "next_step": "review_handoff"},
            reviewer_session_state={"review_required": True, "handoff_status": "pending"},
            bounded_notes=["Current-run continuity only."],
        )
        validated = validate_session_memory(session_memory)
        self.assertEqual(validated["case_context"]["case_id"], "CASE-123")
        self.assertEqual(len(validated["tool_outputs"]), 2)

    def test_session_memory_supports_bounded_reviewer_session_continuity(self) -> None:
        session_memory = build_session_memory(
            case_context={"case_id": "CASE-456", "vendor_name": "Northwind"},
            tool_outputs=[],
            active_reasoning_state={"selected_path": "full_reasoning", "ambiguity_state": "active"},
            reviewer_session_state={
                "review_required": True,
                "review_session_ref": "review-session-001",
                "pending_question_count": 2,
            },
        )
        validated = validate_session_memory(session_memory)
        self.assertTrue(validated["reviewer_session_state"]["review_required"])

    def test_session_memory_missing_required_field_fails_clearly(self) -> None:
        payload = build_session_memory(
            case_context={"case_id": "CASE-789"},
            tool_outputs=[],
            active_reasoning_state={"selected_path": "hybrid"},
            reviewer_session_state={"review_required": True},
        )
        del payload["active_reasoning_state"]
        with self.assertRaisesRegex(ValueError, "active_reasoning_state"):
            validate_session_memory(payload)

    def test_stub_frontier_adapter_returns_bounded_placeholder_response(self) -> None:
        adapter = StubFrontierAdapter()
        request = FrontierJudgmentRequest(
            normalized_case=normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings())),
            uncertainty_section={"missing_information": [], "conflicting_information": [], "uncertainty_flags": []},
            prompt_payload={"prompt_version": "stub-v1"},
            provider_config=FrontierProviderConfig(provider_name="stub", model_name="stub-model"),
        )
        response = adapter.generate_judgment(request)
        self.assertIsInstance(response, FrontierJudgmentResponse)
        self.assertEqual(response.provider_name, "stub")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.parsed_output["case_id"], request.normalized_case["case_id"])
        self.assertEqual(response.parsed_output["confidence"], "low")

    def test_openai_frontier_adapter_can_be_instantiated_cleanly(self) -> None:
        adapter = OpenAIFrontierAdapter()
        self.assertIsInstance(adapter, FrontierAdapter)
        request = FrontierJudgmentRequest(
            normalized_case=normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings())),
            uncertainty_section={"missing_information": [], "conflicting_information": [], "uncertainty_flags": []},
            prompt_payload={"messages": []},
            provider_config=FrontierProviderConfig(provider_name="openai", model_name="gpt-test"),
        )
        response = adapter.generate_judgment(request)
        self.assertEqual(response.provider_name, "openai")
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.provider_metadata["error_code"], "missing_api_key")

    def test_openai_and_stub_adapters_share_the_same_interface(self) -> None:
        self.assertTrue(issubclass(StubFrontierAdapter, FrontierAdapter))
        self.assertTrue(issubclass(OpenAIFrontierAdapter, FrontierAdapter))
        self.assertTrue(callable(getattr(StubFrontierAdapter(), "generate_judgment")))
        self.assertTrue(callable(getattr(OpenAIFrontierAdapter(), "generate_judgment")))

    def test_openai_frontier_adapter_is_mockable_via_injected_transport(self) -> None:
        expected_response = FrontierJudgmentResponse(
            provider_name="openai",
            parsed_output={"exception_type": "missing_po"},
            provider_metadata={"adapter_mode": "test-double"},
        )

        def fake_transport(_: FrontierJudgmentRequest) -> FrontierJudgmentResponse:
            return expected_response

        adapter = OpenAIFrontierAdapter(response_transport=fake_transport)
        request = FrontierJudgmentRequest(
            normalized_case=normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings())),
            uncertainty_section={},
            prompt_payload={},
            provider_config=FrontierProviderConfig(provider_name="openai"),
        )
        self.assertEqual(adapter.generate_judgment(request), expected_response)

    def test_openai_frontier_adapter_live_path_parses_successful_json_response(self) -> None:
        class FakeResponsesClient:
            def __init__(self) -> None:
                self.kwargs = None

            def create(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(
                    id="resp_test_123",
                    output_text=json.dumps(
                        {
                            "exception_type": "missing_po",
                            "reason_summary": "Invoice lacks a usable PO anchor.",
                            "recommended_owner": "buyer_procurement",
                            "priority": "medium",
                            "next_actions": ["Verify whether a valid PO exists for this invoice."],
                            "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                            "confidence": "high",
                        }
                    ),
                    model_dump=lambda: {"id": "resp_test_123", "output_text": "json"},
                )

        fake_responses = FakeResponsesClient()
        fake_client = SimpleNamespace(responses=fake_responses)
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
        prompt_payload = build_frontier_triage_prompt(normalized_case)
        adapter = OpenAIFrontierAdapter(client_factory=lambda api_key, timeout_ms: fake_client)
        request = FrontierJudgmentRequest(
            normalized_case=normalized_case,
            uncertainty_section={"missing_information": [], "conflicting_information": [], "uncertainty_flags": []},
            prompt_payload=prompt_payload,
            provider_config=FrontierProviderConfig(
                provider_name="openai",
                model_name="gpt-test",
                timeout_ms=12345,
                temperature=0.2,
                max_output_tokens=400,
                openai_api_key="test-key",
            ),
        )

        response = adapter.generate_judgment(request)
        self.assertEqual(response.status, "success")
        self.assertEqual(response.parsed_output["exception_type"], "missing_po")
        self.assertEqual(response.provider_metadata["response_id"], "resp_test_123")
        self.assertEqual(response.provider_metadata["model_name"], "gpt-test")
        self.assertEqual(fake_responses.kwargs["model"], "gpt-test")
        self.assertEqual(
            fake_responses.kwargs["input"][0]["content"][0]["text"],
            prompt_payload["system_instructions"],
        )
        self.assertEqual(
            json.loads(fake_responses.kwargs["input"][1]["content"][0]["text"]),
            prompt_payload["user_payload"],
        )

    def test_openai_frontier_adapter_live_path_api_failure_is_bounded(self) -> None:
        class RaisingResponsesClient:
            def create(self, **kwargs):
                raise RuntimeError("boom")

        fake_client = SimpleNamespace(responses=RaisingResponsesClient())
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
        adapter = OpenAIFrontierAdapter(client_factory=lambda api_key, timeout_ms: fake_client)
        request = FrontierJudgmentRequest(
            normalized_case=normalized_case,
            uncertainty_section={},
            prompt_payload=build_frontier_triage_prompt(normalized_case),
            provider_config=FrontierProviderConfig(
                provider_name="openai",
                model_name="gpt-test",
                openai_api_key="test-key",
            ),
        )
        response = adapter.generate_judgment(request)
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.provider_metadata["error_code"], "api_error")

    def test_openai_frontier_adapter_live_path_missing_model_fails_clearly(self) -> None:
        adapter = OpenAIFrontierAdapter()
        request = FrontierJudgmentRequest(
            normalized_case=normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings())),
            uncertainty_section={},
            prompt_payload=build_frontier_triage_prompt(
                normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
            ),
            provider_config=FrontierProviderConfig(
                provider_name="openai",
                model_name=None,
                openai_api_key="test-key",
            ),
        )
        response = adapter.generate_judgment(request)
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.provider_metadata["error_code"], "missing_model")

    def test_openai_frontier_adapter_live_path_invalid_json_fails_clearly(self) -> None:
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    id="resp_bad_json",
                    output_text="{not-valid-json",
                    model_dump=lambda: {"id": "resp_bad_json", "output_text": "{not-valid-json"},
                )
            )
        )
        adapter = OpenAIFrontierAdapter(client_factory=lambda api_key, timeout_ms: fake_client)
        request = FrontierJudgmentRequest(
            normalized_case=normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings())),
            uncertainty_section={},
            prompt_payload=build_frontier_triage_prompt(
                normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
            ),
            provider_config=FrontierProviderConfig(
                provider_name="openai",
                model_name="gpt-test",
                openai_api_key="test-key",
            ),
        )
        response = adapter.generate_judgment(request)
        self.assertEqual(response.status, "failed")
        self.assertEqual(response.provider_metadata["error_code"], "malformed_json")

    def test_business_modules_do_not_import_provider_code_directly(self) -> None:
        business_files = [
            ROOT / "invoice_exception_poc_a" / "main.py",
            ROOT / "invoice_exception_poc_a" / "triage" / "orchestrator.py",
            ROOT / "invoice_exception_poc_a" / "triage" / "classifier.py",
            ROOT / "invoice_exception_poc_a" / "triage" / "reasoning.py",
            ROOT / "invoice_exception_poc_a" / "triage" / "recommender.py",
            ROOT / "invoice_exception_poc_a" / "triage" / "guidance.py",
            ROOT / "invoice_exception_poc_a" / "intake" / "service.py",
            ROOT / "invoice_exception_poc_a" / "normalization" / "service.py",
            ROOT / "invoice_exception_poc_a" / "schema" / "output.py",
        ]
        forbidden_markers = ["import openai", "from openai", "frontier_adapters.openai_adapter"]
        for path in business_files:
            text = path.read_text(encoding="utf-8")
            for marker in forbidden_markers:
                with self.subTest(path=path.name, marker=marker):
                    self.assertNotIn(marker, text)

    def test_frontier_adapter_layer_is_importable_without_business_flow_changes(self) -> None:
        exported = {
            "FrontierAdapter",
            "FrontierJudgmentRequest",
            "FrontierJudgmentResponse",
            "FrontierProviderConfig",
            "get_frontier_adapter",
            "StubFrontierAdapter",
            "OpenAIFrontierAdapter",
        }
        module = __import__("invoice_exception_poc_a.frontier_adapters", fromlist=list(exported))
        self.assertTrue(exported.issubset(set(dir(module))))

    def test_frontier_adapter_factory_returns_expected_adapter(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "stub",
                "FRONTIER_MODEL": "stub-placeholder-v1",
            },
            clear=True,
        ):
            settings = get_settings()
        self.assertIsInstance(get_frontier_adapter(settings), StubFrontierAdapter)

    def test_frontier_prompt_contract_is_versioned(self) -> None:
        self.assertEqual(FRONTIER_TRIAGE_PROMPT_VERSION, "frontier-triage-v1")

    def test_frontier_prompt_for_clean_sample_case_includes_required_fields_and_enums(self) -> None:
        with SAMPLE_CASE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        normalized_case = normalize_case(build_case_envelope(validate_case_payload(payload), get_settings()))
        prompt = build_frontier_triage_prompt(normalized_case)
        self.assertEqual(prompt["contract_version"], FRONTIER_TRIAGE_PROMPT_VERSION)
        for field in REQUIRED_FRONTIER_OUTPUT_FIELDS:
            self.assertIn(field, prompt["system_instructions"])
            self.assertIn(field, prompt["user_payload"]["response_schema_guidance"]["required_fields"])
        for value in EXCEPTION_TAXONOMY:
            self.assertIn(value, prompt["system_instructions"])
        for value in OWNER_CATEGORIES:
            self.assertIn(value, prompt["system_instructions"])
        for value in ALLOWED_CONFIDENCE_VALUES:
            self.assertIn(value, prompt["system_instructions"])
        for value in ALLOWED_PRIORITY_VALUES:
            self.assertIn(value, prompt["system_instructions"])
        self.assertEqual(prompt["user_payload"]["case_id"], normalized_case["case_id"])

    def test_frontier_prompt_for_ambiguous_case_includes_uncertainty_signals(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["vendor_name"] = "Unexpected Vendor"
        payload["invoice"]["payment_terms"] = "NET_90"
        normalized_case = normalize_case(build_case_envelope(payload, get_settings()))
        prompt = build_frontier_triage_prompt(normalized_case)
        uncertainty = prompt["user_payload"]["uncertainty"]
        self.assertTrue(uncertainty["conflicting_information"])
        self.assertIn("missing or conflicting facts", prompt["system_instructions"])
        self.assertEqual(prompt["user_payload"]["normalized_case"]["invoice_facts"]["vendor_name"], "Unexpected Vendor")

    def test_frontier_prompt_for_low_information_case_preserves_missing_information(self) -> None:
        payload = self._valid_minimal_payload()
        payload["invoice"]["invoice_number"] = None
        payload["invoice"]["invoice_amount"] = None
        payload["vendor_master"]["vendor_id"] = None
        normalized_case = normalize_case(build_case_envelope(payload, get_settings()))
        prompt = build_frontier_triage_prompt(normalized_case, prompt_version="frontier-test-v2")
        missing_codes = {
            item["code"] for item in prompt["user_payload"]["uncertainty"]["missing_information"]
        }
        self.assertIn("missing_invoice_number", missing_codes)
        self.assertIn("missing_invoice_amount", missing_codes)
        self.assertIn("missing_vendor_identity", missing_codes)
        self.assertEqual(prompt["prompt_version"], "frontier-test-v2")

    def test_frontier_prompt_enforces_json_only_and_boundary_language(self) -> None:
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), get_settings()))
        prompt = build_frontier_triage_prompt(normalized_case)
        instructions = prompt["system_instructions"]
        required_markers = [
            "Return valid JSON only",
            "Use normalized facts only",
            "Return exactly one primary exception_type",
            "avoid unsupported claims",
            "do not imply autonomous execution",
            "Do not use downstream action language",
            "Do not reference memory, prior cases, prior corrections, or cross-case patterns",
            "Do not route, approve, reject, pay, notify, post to ERP, or use uncontrolled tools",
            "Stay inside PoC A boundaries only",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, instructions)

    def test_frontier_parser_normalizes_valid_stub_payload(self) -> None:
        parsed = parse_frontier_judgment_to_poc_a_output(
            {
                "exception_type": " insufficient_information ",
                "reason_summary": " Stub frontier adapter returned a placeholder bounded judgment. ",
                "recommended_owner": " exception_review_queue ",
                "priority": " low ",
                "next_actions": [" Review the normalized case and replace the stub adapter with a live provider. "],
                "questions_for_reviewer": [" What additional frontier prompt or provider wiring is still needed? "],
                "confidence": " low ",
            },
            case_id="CASE-STUB-001",
        )
        self.assertEqual(parsed["case_id"], "CASE-STUB-001")
        self.assertEqual(parsed["exception_type"], "insufficient_information")
        self.assertEqual(parsed["recommended_owner"], "exception_review_queue")
        self.assertEqual(parsed["priority"], "low")
        self.assertEqual(parsed["confidence"], "low")

    def test_frontier_parser_normalizes_scalar_actions_and_questions_to_lists(self) -> None:
        parsed = parse_frontier_judgment_to_poc_a_output(
            {
                "exception_type": "missing_po",
                "reason_summary": "The invoice does not include a usable PO reference.",
                "recommended_owner": "buyer_procurement",
                "priority": "medium",
                "next_actions": " Verify whether a valid PO exists for this invoice. ",
                "questions_for_reviewer": " Is there a valid PO number for this invoice? ",
                "confidence": "high",
            },
            case_id="CASE-SCALAR-001",
        )
        self.assertEqual(parsed["next_actions"], ["Verify whether a valid PO exists for this invoice."])
        self.assertEqual(parsed["questions_for_reviewer"], ["Is there a valid PO number for this invoice?"])

    def test_frontier_parser_missing_reason_summary_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "reason_summary"):
            parse_frontier_judgment_to_poc_a_output(
                {
                    "exception_type": "missing_po",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "next_actions": ["Verify whether a valid PO exists for this invoice."],
                    "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                    "confidence": "high",
                },
                case_id="CASE-MISSING-001",
            )

    def test_frontier_parser_missing_exception_type_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "exception_type"):
            parse_frontier_judgment_to_poc_a_output(
                {
                    "reason_summary": "Missing exception type.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "next_actions": ["Verify whether a valid PO exists for this invoice."],
                    "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                    "confidence": "high",
                },
                case_id="CASE-MISSING-002",
            )

    def test_frontier_parser_malformed_payload_type_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a dictionary"):
            parse_frontier_judgment_to_poc_a_output("not-a-dict", case_id="CASE-BAD-001")

    def test_frontier_normalizer_builds_schema_shaped_candidate(self) -> None:
        normalized = normalize_frontier_judgment_for_validation(
            {
                "exception_type": " missing_po ",
                "reason_summary": " The invoice does not include a usable PO reference. ",
                "recommended_owner": " buyer_procurement ",
                "priority": " Medium ",
                "next_actions": " Verify whether a valid PO exists for this invoice. ",
                "questions_for_reviewer": " Is there a valid PO number for this invoice? ",
                "confidence": " High ",
            },
            case_id="CASE-NORM-001",
        )
        self.assertEqual(normalized["case_id"], "CASE-NORM-001")
        self.assertEqual(normalized["exception_type"], "missing_po")
        self.assertEqual(normalized["priority"], "Medium")
        self.assertEqual(normalized["confidence"], "High")
        self.assertEqual(normalized["next_actions"], ["Verify whether a valid PO exists for this invoice."])
        self.assertEqual(normalized["questions_for_reviewer"], ["Is there a valid PO number for this invoice?"])

    def test_frontier_run_triage_with_injected_openai_transport_returns_bounded_output(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "reason_summary": "The invoice does not include a usable PO reference for comparison.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "next_actions": ["Verify whether a valid PO exists for this invoice."],
                    "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                    "confidence": "high",
                },
                raw_response={"contract_version": request.prompt_payload["contract_version"]},
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        result = run_triage(normalized_case, settings, [], frontier_adapter_override=adapter)
        self.assertEqual(result["exception_type"], "missing_po")
        self.assertEqual(result["recommended_owner"], "buyer_procurement")
        self.assertEqual(result["priority"], "medium")
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(
            [entry["stage"] for entry in result["execution_trace"]],
            [
                "frontier_prompt_build",
                "frontier_adapter_call",
                "frontier_output_parse",
                "frontier_generation",
            ],
        )

    def test_frontier_output_reuses_shared_validator_as_valid(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "stub",
                "FRONTIER_MODEL": "stub-placeholder-v1",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        triage_result = run_triage(normalized_case, settings, [])
        output = build_placeholder_output(normalized_case, triage_result, settings, latency_ms=5.0)
        self.assertEqual(output["validation_status"], "valid")
        self.assertEqual(output["repair_count"], 0)

    def test_frontier_output_reuses_shared_validator_as_repaired_valid(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "reason_summary": "The invoice does not include a usable PO reference.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "Medium",
                    "next_actions": " Verify whether a valid PO exists for this invoice. ",
                    "questions_for_reviewer": " Is there a valid PO number for this invoice? ",
                    "confidence": "High",
                },
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        triage_result = run_triage(normalized_case, settings, [], frontier_adapter_override=adapter)
        output = build_placeholder_output(normalized_case, triage_result, settings, latency_ms=5.0)
        self.assertEqual(output["validation_status"], "repaired_valid")
        self.assertTrue(output["repair_attempted"])
        self.assertEqual(output["repair_count"], 1)

    def test_frontier_output_reuses_shared_validator_as_failed(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "next_actions": ["Verify whether a valid PO exists for this invoice."],
                    "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                    "confidence": "high",
                },
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        triage_result = run_triage(normalized_case, settings, [], frontier_adapter_override=adapter)
        output = build_placeholder_output(normalized_case, triage_result, settings, latency_ms=5.0)
        self.assertEqual(output["validation_status"], "failed")
        self.assertFalse(output["repair_attempted"])
        self.assertTrue(any("reason_summary" in error for error in output["validation_errors"]))

    def test_frontier_adapter_failure_is_surfaced_clearly(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        trace: list[dict] = []
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={},
                provider_metadata={"adapter_mode": "test-double"},
                status="failed",
            )
        )
        with self.assertRaisesRegex(ValueError, "Frontier triage generation failed"):
            run_triage(normalized_case, settings, trace, frontier_adapter_override=adapter)
        self.assertEqual(
            trace,
            [
                {
                    "stage": "frontier_prompt_build",
                    "status": "completed",
                    "note": "Built frontier prompt contract 'frontier-triage-v1'.",
                },
                {
                    "stage": "frontier_adapter_call",
                    "status": "failed",
                    "note": "Frontier adapter 'openai' returned status 'failed'.",
                },
            ],
        )

    def test_frontier_incomplete_adapter_payload_reaches_shared_validation_failure(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        trace: list[dict] = []
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "reason_summary": "Incomplete payload.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "confidence": "high",
                },
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        triage_result = run_triage(normalized_case, settings, trace, frontier_adapter_override=adapter)
        output = build_placeholder_output(normalized_case, triage_result, settings, latency_ms=5.0)
        self.assertEqual(
            [entry["stage"] for entry in trace],
            ["frontier_prompt_build", "frontier_adapter_call", "frontier_output_parse", "frontier_generation"],
        )
        parse_stage = trace[2]
        self.assertEqual(parse_stage["status"], "completed")
        self.assertIn("parsed and normalized", parse_stage["note"].lower())
        self.assertEqual(output["validation_status"], "failed")
        self.assertTrue(
            any("next_actions" in error or "questions_for_reviewer" in error for error in output["validation_errors"])
        )

    def test_frontier_invalid_enum_uses_shared_failure_handling_only(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "reason_summary": "The invoice does not include a usable PO reference.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "urgent",
                    "next_actions": ["Verify whether a valid PO exists for this invoice."],
                    "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                    "confidence": "high",
                },
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        triage_result = run_triage(normalized_case, settings, [], frontier_adapter_override=adapter)
        output = build_placeholder_output(normalized_case, triage_result, settings, latency_ms=5.0)
        self.assertEqual(output["validation_status"], "failed")
        self.assertTrue(any("priority" in error for error in output["validation_errors"]))

    def test_frontier_run_triage_normalizes_scalar_actions_and_questions_from_adapter(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRIAGE_ENGINE": "frontier",
                "FRONTIER_PROVIDER": "openai",
                "FRONTIER_MODEL": "gpt-test",
            },
            clear=True,
        ):
            settings = get_settings()
        normalized_case = normalize_case(build_case_envelope(self._valid_minimal_payload(), settings))
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "reason_summary": "The invoice does not include a usable PO reference.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "next_actions": " Verify whether a valid PO exists for this invoice. ",
                    "questions_for_reviewer": " Is there a valid PO number for this invoice? ",
                    "confidence": "high",
                },
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        result = run_triage(normalized_case, settings, [], frontier_adapter_override=adapter)
        self.assertEqual(result["next_actions"], ["Verify whether a valid PO exists for this invoice."])
        self.assertEqual(result["questions_for_reviewer"], ["Is there a valid PO number for this invoice?"])

    def test_dual_run_runner_executes_simple_case_in_both_modes(self) -> None:
        dataset_case = load_dataset_case("amount_mismatch_simple.json")
        record = build_comparison_record(dataset_case)
        self.assertEqual(record["case_id"], dataset_case["case_id"])
        self.assertEqual(record["coverage_bucket"], "simple_obvious")
        self.assertEqual(record["deterministic_output"]["case_id"], dataset_case["case_id"])
        self.assertEqual(record["frontier_output"]["case_id"], dataset_case["case_id"])
        self.assertEqual(record["deterministic_output"]["run_metadata"]["triage_engine"], "deterministic")
        self.assertEqual(record["frontier_output"]["run_metadata"]["triage_engine"], "frontier")

    def test_dual_run_runner_executes_ambiguous_case_in_both_modes(self) -> None:
        dataset_case = load_dataset_case("mixed_signal_ambiguous.json")
        record = build_comparison_record(dataset_case)
        self.assertEqual(record["case_id"], "EVAL-AMBIG-001")
        self.assertEqual(record["coverage_bucket"], "moderately_ambiguous")
        self.assertIn("deterministic_output", record)
        self.assertIn("frontier_output", record)

    def test_dual_run_report_preserves_case_ids_and_engine_separated_outputs(self) -> None:
        report = build_dual_run_comparison_report(case_filenames=["missing_po_simple.json"])
        self.assertEqual(len(report["records"]), 1)
        record = report["records"][0]
        self.assertEqual(record["case_id"], record["deterministic_output"]["case_id"])
        self.assertEqual(record["case_id"], record["frontier_output"]["case_id"])
        self.assertIn("reviewer_notes", record)

    def test_dual_run_report_supports_injected_openai_test_transport_without_credentials(self) -> None:
        adapter = OpenAIFrontierAdapter(
            response_transport=lambda _request: FrontierJudgmentResponse(
                provider_name="openai",
                parsed_output={
                    "exception_type": "missing_po",
                    "reason_summary": "The invoice does not include a usable PO reference.",
                    "recommended_owner": "buyer_procurement",
                    "priority": "medium",
                    "next_actions": ["Verify whether a valid PO exists for this invoice."],
                    "questions_for_reviewer": ["Is there a valid PO number for this invoice?"],
                    "confidence": "high",
                },
                provider_metadata={"adapter_mode": "test-double"},
                status="success",
            )
        )
        report = build_dual_run_comparison_report(
            case_filenames=["missing_po_simple.json"],
            frontier_provider="openai",
            frontier_model="gpt-test",
            frontier_adapter_override=adapter,
        )
        record = report["records"][0]
        self.assertEqual(record["frontier_output"]["exception_type"], "missing_po")
        self.assertEqual(record["frontier_output"]["run_metadata"]["triage_engine"], "frontier")

    def test_run_case_for_engine_keeps_deterministic_baseline_behavior(self) -> None:
        dataset_case = load_dataset_case("receiving_mismatch_simple.json")
        result = run_case_for_engine(dataset_case["input_payload"], engine_mode="deterministic")
        output = result["output_payload"]
        self.assertEqual(result["engine_mode"], "deterministic")
        self.assertEqual(output["run_metadata"]["triage_engine"], "deterministic")
        self.assertEqual(output["validation_status"], "valid")

    def test_deterministic_trace_order_remains_unchanged(self) -> None:
        result = self.run_app(SAMPLE_CASE)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        trace = json.loads(result.stdout)["execution_trace"]
        self.assertEqual(
            [entry["stage"] for entry in trace],
            [
                "triage_engine_selection",
                "intake",
                "normalization",
                "classification",
                "reason_summary",
                "recommendation",
                "guidance",
                "schema_validation",
                "output_assembly",
            ],
        )

    def test_multi_case_input_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump([{"case_id": "A"}, {"case_id": "B"}], handle)
            temp_path = Path(handle.name)

        try:
            result = self.run_app(temp_path)
            self.assertNotEqual(result.returncode, 0)
            combined_output = f"{result.stdout}\n{result.stderr}"
            self.assertIn("exactly one case", combined_output)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_dataset_wrapper_input_is_accepted_by_cli(self) -> None:
        dataset_case = (
            ROOT
            / "invoice_exception_poc_a"
            / "evaluation"
            / "dataset_pack"
            / "cases"
            / "mixed_signal_ambiguous.json"
        )
        result = self.run_app(dataset_case, {"TRIAGE_ENGINE": "deterministic"})
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["case_id"], "EVAL-AMBIG-001")
        self.assertEqual(payload["run_metadata"]["triage_engine"], "deterministic")

    def test_load_case_unwraps_dataset_case_wrapper(self) -> None:
        dataset_case = (
            ROOT
            / "invoice_exception_poc_a"
            / "evaluation"
            / "dataset_pack"
            / "cases"
            / "mixed_signal_ambiguous.json"
        )
        loaded_case = load_case(dataset_case)
        self.assertEqual(loaded_case["case_id"], "EVAL-AMBIG-001")
        self.assertIn("invoice", loaded_case)
        self.assertIn("po_summary", loaded_case)

    def test_wrapped_multi_case_payload_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"cases": [{"case_id": "A"}, {"case_id": "B"}]}, handle)
            temp_path = Path(handle.name)

        try:
            result = self.run_app(temp_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple cases", f"{result.stdout}\n{result.stderr}")
        finally:
            temp_path.unlink(missing_ok=True)

    def test_workflow_version_is_externally_configurable(self) -> None:
        result = self.run_app(SAMPLE_CASE, {"WORKFLOW_VERSION": "9.9.9"})
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["workflow_version"], "9.9.9")

    def test_no_cross_case_memory_component_present(self) -> None:
        settings = get_settings()
        self.assertFalse(hasattr(settings, "database_url"))
        self.assertFalse(hasattr(settings, "memory_store"))
        self.assertEqual(settings.workflow_version, os.getenv("WORKFLOW_VERSION", "0.1.0"))

    def test_guardrails_define_unsupported_capabilities_explicitly(self) -> None:
        snapshot = get_guardrails_snapshot()
        self.assertTrue(snapshot["stateless_across_cases"])
        self.assertFalse(snapshot["downstream_actions_enabled"])
        self.assertFalse(snapshot["feedback_persistence_enabled"])
        self.assertFalse(snapshot["prior_case_retrieval_enabled"])
        self.assertEqual(snapshot["unsupported_capabilities"], list(UNSUPPORTED_CAPABILITIES))

    def test_prior_case_retrieval_is_explicitly_blocked(self) -> None:
        with self.assertRaises(ScopeGuardrailError):
            assert_capability_supported("prior_case_retrieval")

    def test_feedback_reuse_is_explicitly_blocked(self) -> None:
        with self.assertRaises(ScopeGuardrailError):
            assert_capability_supported("feedback_reuse")

    def test_downstream_actions_are_explicitly_blocked(self) -> None:
        blocked = [
            "autonomous_routing",
            "approve_action",
            "reject_action",
            "pay_action",
            "outbound_communication",
        ]
        for capability in blocked:
            with self.subTest(capability=capability):
                with self.assertRaises(ScopeGuardrailError):
                    assert_capability_supported(capability)

    def test_missing_case_id_fails_validation(self) -> None:
        payload = self._valid_minimal_payload()
        del payload["case_id"]
        with self.assertRaisesRegex(ValueError, "case_id"):
            validate_case_payload(payload)

    def test_missing_invoice_fails_validation(self) -> None:
        payload = self._valid_minimal_payload()
        del payload["invoice"]
        with self.assertRaisesRegex(ValueError, "invoice"):
            validate_case_payload(payload)

    def test_missing_po_summary_fails_validation(self) -> None:
        payload = self._valid_minimal_payload()
        del payload["po_summary"]
        with self.assertRaisesRegex(ValueError, "po_summary"):
            validate_case_payload(payload)

    def test_missing_vendor_master_fails_validation(self) -> None:
        payload = self._valid_minimal_payload()
        del payload["vendor_master"]
        with self.assertRaisesRegex(ValueError, "vendor_master"):
            validate_case_payload(payload)

    def test_missing_policy_rules_fails_validation(self) -> None:
        payload = self._valid_minimal_payload()
        del payload["policy_rules"]
        with self.assertRaisesRegex(ValueError, "policy_rules"):
            validate_case_payload(payload)

    def _valid_minimal_payload(self) -> dict:
        return {
            "case_id": "CASE-TEST-001",
            "invoice": {
                "invoice_number": "INV-001",
                "vendor_name": "Vendor One",
                "invoice_amount": 150.0,
                "currency": "USD",
                "payment_terms": "NET_30",
            },
            "po_summary": {
                "po_number": "PO-001",
                "buyer_name": "Buyer One",
                "po_amount": 150.0,
                "currency": "USD",
                "line_summary": "PO line one",
            },
            "vendor_master": {
                "vendor_id": "VEN-001",
                "vendor_name": "Vendor One",
                "payment_terms": "NET_30",
                "payment_method": "ACH",
                "vendor_status": "ACTIVE",
            },
            "policy_rules": {
                "tolerance_threshold_percent": 3.0,
                "tolerance_threshold_amount": 50.0,
                "routing_guidance": "Route to analyst review.",
                "policy_anchor_reference": "POL-001",
            },
        }

    def _sample_operational_outputs(self) -> list[dict]:
        return [
            {
                "validation_status": "valid",
                "run_metadata": {
                    "latency_ms": 2.0,
                    "retry_count": 0,
                    "token_usage": None,
                    "compute_usage": None,
                },
            },
            {
                "validation_status": "repaired_valid",
                "run_metadata": {
                    "latency_ms": 3.0,
                    "retry_count": 1,
                    "token_usage": None,
                    "compute_usage": None,
                },
            },
            {
                "validation_status": "failed",
                "run_metadata": {
                    "latency_ms": 2.5,
                    "retry_count": 0,
                    "token_usage": None,
                    "compute_usage": None,
                },
            },
        ]

    def test_frontier_demo_case_set_artifact_exists(self) -> None:
        demo_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "frontier_demo_case_set.json"
        self.assertTrue(demo_path.exists())

    def test_frontier_demo_case_set_covers_required_categories(self) -> None:
        demo_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "frontier_demo_case_set.json"
        with demo_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertEqual(payload["demo_case_set_name"], "poc_a_f_frontier_demo_case_set")
        self.assertEqual(len(payload["cases"]), 4)
        self.assertEqual(
            {case["coverage_category"] for case in payload["cases"]},
            {
                "happy_path_receiving_mismatch",
                "missing_po",
                "mixed_signal_ambiguous",
                "insufficient_information_low_data",
            },
        )

    def test_frontier_demo_case_set_paths_and_notes_are_valid(self) -> None:
        demo_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "frontier_demo_case_set.json"
        with demo_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        expected_case_ids = {
            "CASE-POCA-001": "samples/sample_case.json",
            "EVAL-MISSINGPO-001": "invoice_exception_poc_a/evaluation/dataset_pack/cases/missing_po_simple.json",
            "EVAL-AMBIG-001": "invoice_exception_poc_a/evaluation/dataset_pack/cases/mixed_signal_ambiguous.json",
            "EVAL-LOWDATA-001": "invoice_exception_poc_a/evaluation/dataset_pack/cases/insufficient_information_edge.json",
        }

        for case in payload["cases"]:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(case["file_path"], expected_case_ids[case["case_id"]])
                self.assertTrue((ROOT / case["file_path"]).exists())
                self.assertTrue(case["why_included"].strip())
                self.assertTrue(case["what_to_notice"].strip())
                self.assertIn(
                    case["comparison_emphasis"],
                    {
                        "side_by_side",
                        "deterministic_or_side_by_side",
                        "frontier_or_side_by_side",
                    },
                )

    def test_readme_demo_case_section_references_valid_paths(self) -> None:
        readme_path = ROOT / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8")
        self.assertIn("## Frontier Demo Case Set", readme_text)

        documented_paths = [
            "invoice_exception_poc_a/evaluation/frontier_demo_case_set.json",
            "samples/sample_case.json",
            "invoice_exception_poc_a/evaluation/dataset_pack/cases/missing_po_simple.json",
            "invoice_exception_poc_a/evaluation/dataset_pack/cases/mixed_signal_ambiguous.json",
            "invoice_exception_poc_a/evaluation/dataset_pack/cases/insufficient_information_edge.json",
        ]
        for relative_path in documented_paths:
            with self.subTest(path=relative_path):
                self.assertIn(relative_path, readme_text)
                self.assertTrue((ROOT / relative_path).exists())

    def test_frontier_demo_script_artifact_exists(self) -> None:
        script_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "frontier_demo_script.md"
        self.assertTrue(script_path.exists())

    def test_frontier_demo_script_references_selected_case_set(self) -> None:
        script_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "frontier_demo_script.md"
        script_text = script_path.read_text(encoding="utf-8")
        referenced_paths = [
            "samples/sample_case.json",
            "invoice_exception_poc_a/evaluation/dataset_pack/cases/missing_po_simple.json",
            "invoice_exception_poc_a/evaluation/dataset_pack/cases/mixed_signal_ambiguous.json",
            "invoice_exception_poc_a/evaluation/dataset_pack/cases/insufficient_information_edge.json",
        ]
        for relative_path in referenced_paths:
            with self.subTest(path=relative_path):
                self.assertIn(relative_path, script_text)
                self.assertTrue((ROOT / relative_path).exists())

    def test_frontier_demo_script_contains_required_framing_and_sections(self) -> None:
        script_path = ROOT / "invoice_exception_poc_a" / "evaluation" / "frontier_demo_script.md"
        script_text = script_path.read_text(encoding="utf-8")
        required_markers = [
            "## Opening framing",
            "deterministic",
            "frontier",
            "bounded judgment layer",
            "not autonomous workflow execution",
            "## Case-by-case talk track",
            "### Case 1: Happy path / receiving mismatch",
            "### Case 2: Missing PO",
            "### Case 3: Mixed-signal ambiguous",
            "### Case 4: Insufficient information / low-data edge",
            "## Comparison interpretation",
            "## Closing summary",
        ]
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, script_text)

    def test_readme_demo_script_section_references_valid_paths(self) -> None:
        readme_path = ROOT / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8")
        self.assertIn("## Frontier Demo Script", readme_text)
        documented_paths = [
            "invoice_exception_poc_a/evaluation/frontier_demo_script.md",
            "invoice_exception_poc_a/evaluation/frontier_demo_case_set.json",
        ]
        for relative_path in documented_paths:
            with self.subTest(path=relative_path):
                self.assertIn(relative_path, readme_text)
                self.assertTrue((ROOT / relative_path).exists())


if __name__ == "__main__":
    unittest.main()
