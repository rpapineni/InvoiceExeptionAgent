"""Environment-driven settings for the PoC A scaffold."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    workflow_version: str = "0.1.0"
    prompt_version: str = "placeholder-prompt-v1"
    app_env: str = "local"


def get_settings() -> Settings:
    """Load externally configurable version identifiers."""
    return Settings(
        workflow_version=os.getenv("WORKFLOW_VERSION", "0.1.0"),
        prompt_version=os.getenv("PROMPT_VERSION", "placeholder-prompt-v1"),
        app_env=os.getenv("APP_ENV", "local"),
    )
