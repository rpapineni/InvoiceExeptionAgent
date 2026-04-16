"""Reusable evaluation dataset pack helpers for PoC A."""

from __future__ import annotations

import json
from pathlib import Path


DATASET_PACK_DIR = Path(__file__).resolve().parent / "dataset_pack"
DATASET_CASES_DIR = DATASET_PACK_DIR / "cases"
DATASET_MANIFEST_PATH = DATASET_PACK_DIR / "manifest.json"


def load_dataset_manifest() -> dict:
    """Load the PoC A evaluation dataset manifest."""
    with DATASET_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_dataset_case(case_filename: str) -> dict:
    """Load one dataset case file by filename."""
    with (DATASET_CASES_DIR / case_filename).open("r", encoding="utf-8") as handle:
        return json.load(handle)

