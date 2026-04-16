"""Basic tests for the bounded PoC A scaffold."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from invoice_exception_poc_a.config.settings import get_settings
from invoice_exception_poc_a.evaluation.acceptance_report import (
    POC_A_ACCEPTANCE_CRITERIA,
    create_acceptance_report_template,
)
from invoice_exception_poc_a.evaluation.dataset import load_dataset_case, load_dataset_manifest
from invoice_exception_poc_a.evaluation.operational_metrics import create_operational_metrics_report
from invoice_exception_poc_a.evaluation.scoring import (
    BUSINESS_QUALITY_METRICS,
    create_all_score_records,
    create_score_record,
)
from invoice_exception_poc_a.guardrails.policy import (
    UNSUPPORTED_CAPABILITIES,
    ScopeGuardrailError,
    assert_capability_supported,
    get_guardrails_snapshot,
)
from invoice_exception_poc_a.intake.contract import OPTIONAL_TOP_LEVEL_FIELDS, REQUIRED_TOP_LEVEL_FIELDS
from invoice_exception_poc_a.intake.service import build_case_envelope, validate_case_payload
from invoice_exception_poc_a.schema.model import (
    ALLOWED_CONFIDENCE_VALUES,
    ALLOWED_PRIORITY_VALUES,
    ALLOWED_VALIDATION_STATUSES,
    OUTPUT_REQUIRED_FIELDS,
)
from invoice_exception_poc_a.schema.output import SCHEMA_VERSION, build_placeholder_output
from invoice_exception_poc_a.schema.validation import validate_output_payload
from invoice_exception_poc_a.normalization.service import normalize_case
from invoice_exception_poc_a.triage.classifier import classify_primary_exception
from invoice_exception_poc_a.triage.guidance import generate_reviewer_guidance
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


if __name__ == "__main__":
    unittest.main()
