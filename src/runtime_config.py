from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
PLACEHOLDER_KEYS = {"", "your-anthropic-api-key-here", "sk-ant-your-key-here"}


def load_runtime_env() -> None:
    load_dotenv(dotenv_path=ENV_PATH, override=False)


load_runtime_env()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
HAS_REAL_ANTHROPIC_KEY = ANTHROPIC_API_KEY not in PLACEHOLDER_KEYS
DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().lower() == "true"
USE_DEMO_MODE = DEMO_MODE or not HAS_REAL_ANTHROPIC_KEY
