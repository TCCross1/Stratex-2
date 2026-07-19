"""Focused verifier for Wave2A test payload salting.

This script does not modify product code or the database. It imports the test
helper and proves whether two different pytest-session suffixes can still emit
the same PNG payload hash.
"""

import hashlib
import importlib.util
from pathlib import Path


MODULE_PATH = Path("/app/backend/tests/test_nextgen_wave2a.py")


def load_wave2a_module():
    spec = importlib.util.spec_from_file_location("wave2a_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha_for(module, suffix: int, seed: int = 1) -> str:
    module._TEST_SUFFIX = str(suffix)
    return hashlib.sha256(module._png_bytes(seed=seed)).hexdigest()


if __name__ == "__main__":
    wave2a = load_wave2a_module()
    base = int(wave2a._TEST_SUFFIX)
    colliding = base + 65536
    base_sha = sha_for(wave2a, base)
    colliding_sha = sha_for(wave2a, colliding)
    print(f"base_suffix={base}")
    print(f"colliding_suffix={colliding}")
    print(f"base_sha={base_sha}")
    print(f"colliding_sha={colliding_sha}")
    print(f"hashes_equal={base_sha == colliding_sha}")
    raise SystemExit(1 if base_sha == colliding_sha else 0)