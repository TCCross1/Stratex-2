"""Pytest bootstrap — make backend package modules importable from either
`pytest backend/tests` (repo root) or `pytest tests` (backend cwd).
"""
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Repo-root import of `tests.fake_mongo` also needs the repo root on path.
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Stable defaults so nextgen.db import asserts succeed in unit tests.
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_cp002_unit")
