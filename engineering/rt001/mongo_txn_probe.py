#!/usr/bin/env python3
"""RT-001 Mongo transaction capability probe.

Connects to MONGO_URL (from env or .rt001/secrets.env) and attempts a
multi-document transaction. When no replica set / Docker / pymongo is
available, reports INTEGRATION_ENVIRONMENT_UNAVAILABLE and exits 0.

Production readiness: NOT READY.
Base SHA: 0c09b0cf44fb133852ddbb9ce96cea2e137ade6d
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_RT001 = Path(__file__).resolve().parent
if str(_RT001) not in sys.path:
    sys.path.insert(0, str(_RT001))

from _common import (  # noqa: E402
    REPO_ROOT,
    SECRETS_FILE,
    STATUS_OK,
    STATUS_SKIP,
    STATUS_UNAVAILABLE,
    ProbeResult,
    docker_available,
    load_dotenv_file,
    print_result,
)


def _probe() -> ProbeResult:
    load_dotenv_file(_RT001 / ".env.example")
    load_dotenv_file(SECRETS_FILE)

    result = ProbeResult(name="mongo_transaction_probe", status=STATUS_OK, available=False)

    try:
        from pymongo import MongoClient
        from pymongo.errors import OperationFailure, PyMongoError
    except ImportError as exc:
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: pymongo not importable ({exc})")
        return result

    mongo_url = os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI")
    if not mongo_url:
        # Without Docker there is typically no local replica set — honest skip.
        dock = docker_available()
        if not dock.available:
            result.status = STATUS_UNAVAILABLE
            result.extend(f"{STATUS_UNAVAILABLE}: no MONGO_URL and Docker unavailable")
            result.messages.extend(dock.messages)
            return result
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: MONGO_URL not set (run generate_local_secrets.sh / start.sh)")
        return result

    db_name = os.environ.get("DB_NAME", "stratex_rt001")
    # Never log the URL (may contain credentials in other envs).
    result.extend("MONGO_URL present (value not logged)")

    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
        hello = client.admin.command("hello")
    except Exception as exc:  # connection / DNS / timeout
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: Mongo connection failed ({type(exc).__name__})")
        return result

    set_name = hello.get("setName")
    if not set_name:
        result.status = STATUS_SKIP
        result.extend(
            f"{STATUS_SKIP}: Mongo reachable but not a replica set — "
            "transactions unavailable (not a PASS)"
        )
        client.close()
        return result

    result.extend(f"replica set detected: {set_name}")
    db = client[db_name]
    coll_a = db["rt001_txn_a"]
    coll_b = db["rt001_txn_b"]
    marker = f"rt001-{os.getpid()}"

    try:
        with client.start_session() as session:
            with session.start_transaction():
                coll_a.insert_one({"_id": marker, "lane": "LANE_5_RUNTIME_QE"}, session=session)
                coll_b.insert_one({"_id": marker, "ok": True}, session=session)
        # Cleanup outside txn
        coll_a.delete_one({"_id": marker})
        coll_b.delete_one({"_id": marker})
        result.available = True
        result.status = STATUS_OK
        result.extend("multi-document transaction succeeded (local integration only; NOT production)")
    except OperationFailure as exc:
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: transaction OperationFailure ({exc.code})")
    except PyMongoError as exc:
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: transaction failed ({type(exc).__name__})")
    finally:
        client.close()

    return result


def main() -> int:
    # Silence unused import lint for REPO_ROOT when imported as library
    _ = REPO_ROOT
    return print_result(_probe())


if __name__ == "__main__":
    raise SystemExit(main())
