"""
Field-test mission seal key resolution.

Official field-test paths honor MISSION_SEAL_KEY from the environment when set.
When unset, fall back to the documented demo key with an explicit warning.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Literal, Tuple

logger = logging.getLogger("stratex.field_test_seal_key")

DEMO_SEAL_KEY = b"field-test-demo-key"
SealKeySource = Literal["env", "demo_fallback"]

_DEMO_KEY_WARNING_EMITTED = False


def resolve_field_test_seal_key(*, warn_on_fallback: bool = True) -> Tuple[bytes, SealKeySource]:
    """
    Resolve the mission package HMAC key for field-test pipeline and demos.

    Priority:
      1. MISSION_SEAL_KEY environment variable (non-empty)
      2. DEMO_SEAL_KEY with a loud stderr + log warning
    """
    raw = (os.environ.get("MISSION_SEAL_KEY") or "").strip()
    if raw:
        return raw.encode("utf-8"), "env"

    if warn_on_fallback:
        _emit_demo_key_warning()

    return DEMO_SEAL_KEY, "demo_fallback"


def _emit_demo_key_warning() -> None:
    global _DEMO_KEY_WARNING_EMITTED
    if _DEMO_KEY_WARNING_EMITTED:
        return
    _DEMO_KEY_WARNING_EMITTED = True
    message = (
        "WARNING: MISSION_SEAL_KEY is not set — using insecure field-test demo key "
        "'field-test-demo-key'. Export MISSION_SEAL_KEY before field-test publish."
    )
    logger.warning(message)
    print(message, file=sys.stderr)


def reset_demo_key_warning_for_tests() -> None:
    """Test helper — allow warning emission to be exercised again."""
    global _DEMO_KEY_WARNING_EMITTED
    _DEMO_KEY_WARNING_EMITTED = False
