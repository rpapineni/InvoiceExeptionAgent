"""Bounded similar-case retrieval contract helpers for PoC B."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from invoice_exception_poc_a.memory.summary import validate_reviewed_case_summary


ALLOWED_RETRIEVAL_SOURCE_TYPES = (
    "reviewed_case_summary",
    "policy_snippet",
    "vendor_pattern",
    "routing_precedent",
)

RETRIEVAL_CONTRACT_REQUIRED_FIELDS = (
    "retrieval_scope",
    "source_type",
    "source_ref",
    "source_summary",
    "relevance_hint",
)


@dataclass(frozen=True)
class PocBSimilarCaseRetrievalArtifact:
    """Bounded retrieval-artifact representation for later PoC B reuse."""

    retrieval_scope: str
    source_type: str
    source_ref: str
    source_summary: str
    relevance_hint: str
    retrieval_layer: str = "bounded_retrieval_contract"
    vendor_ref: str | None = None
    policy_ref: str | None = None
    precedent_ref: str | None = None
    bounded_notes: list[str] = field(default_factory=list)


def build_similar_case_retrieval_artifact(
    *,
    retrieval_scope: str,
    source_type: str,
    source_ref: str,
    source_summary: str,
    relevance_hint: str,
    source_payload: dict | None = None,
    retrieval_layer: str = "bounded_retrieval_contract",
    vendor_ref: str | None = None,
    policy_ref: str | None = None,
    precedent_ref: str | None = None,
    bounded_notes: list[str] | None = None,
) -> dict:
    """Create a bounded retrieval-contract artifact without executing retrieval."""
    if source_type == "reviewed_case_summary":
        if source_payload is None:
            raise ValueError("Field 'source_payload' is required for source_type 'reviewed_case_summary'.")
        validate_reviewed_case_summary(source_payload)
    elif source_type == "policy_snippet":
        if source_payload is not None and (
            not isinstance(source_payload, dict)
            or not any(
                isinstance(source_payload.get(field_name), str) and source_payload.get(field_name, "").strip()
                for field_name in ("policy_ref", "policy_anchor_reference", "snippet")
            )
        ):
            raise ValueError(
                "Field 'source_payload' for source_type 'policy_snippet' must contain a bounded policy reference."
            )
    elif source_type == "vendor_pattern":
        if source_payload is not None and (
            not isinstance(source_payload, dict)
            or not any(
                isinstance(source_payload.get(field_name), str) and source_payload.get(field_name, "").strip()
                for field_name in ("vendor_id", "vendor_name", "vendor_ref")
            )
        ):
            raise ValueError(
                "Field 'source_payload' for source_type 'vendor_pattern' must contain a bounded vendor reference."
            )
    elif source_type == "routing_precedent":
        if source_payload is not None and (
            not isinstance(source_payload, dict)
            or not any(
                isinstance(source_payload.get(field_name), str) and source_payload.get(field_name, "").strip()
                for field_name in ("owner", "route", "precedent_ref")
            )
        ):
            raise ValueError(
                "Field 'source_payload' for source_type 'routing_precedent' must contain a bounded routing reference."
            )

    artifact = PocBSimilarCaseRetrievalArtifact(
        retrieval_scope=retrieval_scope,
        source_type=source_type,
        source_ref=source_ref,
        source_summary=source_summary,
        relevance_hint=relevance_hint,
        retrieval_layer=retrieval_layer,
        vendor_ref=vendor_ref,
        policy_ref=policy_ref,
        precedent_ref=precedent_ref,
        bounded_notes=bounded_notes or ["Retrieval contract artifact only; no live fetch executed."],
    )
    return asdict(artifact)


def validate_similar_case_retrieval_artifact(payload: dict) -> dict:
    """Validate the bounded similar-case retrieval contract."""
    missing_fields = [field_name for field_name in RETRIEVAL_CONTRACT_REQUIRED_FIELDS if field_name not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Similar-case retrieval artifact is missing required field(s): {missing}.")

    for string_field in RETRIEVAL_CONTRACT_REQUIRED_FIELDS + ("retrieval_layer",):
        if string_field in payload:
            value = payload[string_field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Field '{string_field}' must be a non-empty string.")

    if payload["source_type"] not in ALLOWED_RETRIEVAL_SOURCE_TYPES:
        allowed = ", ".join(ALLOWED_RETRIEVAL_SOURCE_TYPES)
        raise ValueError(f"Field 'source_type' must be one of: {allowed}.")

    for optional_string in ("vendor_ref", "policy_ref", "precedent_ref"):
        if optional_string in payload and payload[optional_string] is not None:
            value = payload[optional_string]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Field '{optional_string}' must be null or a non-empty string.")

    if "bounded_notes" in payload:
        bounded_notes = payload["bounded_notes"]
        if not isinstance(bounded_notes, list) or any(
            not isinstance(note, str) or not note.strip() for note in bounded_notes
        ):
            raise ValueError("Field 'bounded_notes' must be a list of non-empty strings.")

    forbidden_fragments = ("chain-of-thought", "raw_response", "output_text", "prompt", "provider", "trace dump")
    for field_name in ("source_summary", "relevance_hint"):
        lower_value = payload[field_name].lower()
        if any(fragment in lower_value for fragment in forbidden_fragments):
            raise ValueError(f"Field '{field_name}' contains disallowed verbose or unsafe content.")

    return payload
