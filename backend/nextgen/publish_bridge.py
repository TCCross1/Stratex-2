"""
Publish Bridge — Field Test v1

Takes a publication_request from mission_to_passport / deliverables_package
and submits it through the existing governed_publish_service.

This is the only approved path from sealed mission packages into Passport.
Does not invent expected state — caller must supply expected_revision or
expected_head_hash (or they must already be on the publication_request).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .governed_publish_service import governed_publish
from .passport_errors import (
    MissingExpectedStateError,
    StaleExpectedStateError,
    PassportAppendError,
    TransactionUnavailableError,
    IndexReadinessError,
    IdempotencyConflictError,
)


async def publish_sealed_package(
    publication_request: Dict[str, Any],
    *,
    actor_id: str,
    actor_role: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit a prepared publication_request to the single governed publisher.
    """
    required = ("tenant_id", "property_id", "source_type", "source_id", "entry_type", "payload")
    missing = [k for k in required if not publication_request.get(k)]
    if missing:
        return {
            "status": "REJECTED",
            "reason": "MISSING_FIELDS",
            "missing": missing,
        }

    expected_revision = publication_request.get("expected_revision")
    expected_head_hash = publication_request.get("expected_head_hash")
    if expected_revision is None and not expected_head_hash:
        return {
            "status": "REJECTED",
            "reason": "MISSING_EXPECTED_STATE",
            "message": "Provide expected_revision or expected_head_hash before publish.",
        }

    try:
        result = await governed_publish(
            tenant_id=publication_request["tenant_id"],
            property_id=publication_request["property_id"],
            source_type=publication_request["source_type"],
            source_id=publication_request["source_id"],
            entry_type=publication_request["entry_type"],
            payload=publication_request["payload"],
            actor_id=actor_id,
            actor_role=actor_role,
            correlation_id=correlation_id,
            idempotency_key=publication_request.get("idempotency_key"),
            expected_revision=expected_revision,
            expected_head_hash=expected_head_hash,
        )
        return {
            "status": "PUBLISHED",
            "result": result,
        }
    except MissingExpectedStateError as e:
        return {"status": "REJECTED", "reason": "MISSING_EXPECTED_STATE", "message": str(e)}
    except StaleExpectedStateError as e:
        return {"status": "CONFLICT", "reason": "STALE_EXPECTED_STATE", "message": str(e)}
    except IdempotencyConflictError as e:
        return {"status": "CONFLICT", "reason": "IDEMPOTENCY_CONFLICT", "message": str(e)}
    except TransactionUnavailableError as e:
        return {"status": "UNAVAILABLE", "reason": "TRANSACTION_UNAVAILABLE", "message": str(e)}
    except IndexReadinessError as e:
        return {"status": "UNAVAILABLE", "reason": "INDEX_NOT_READY", "message": str(e)}
    except PassportAppendError as e:
        return {"status": "FAILED", "reason": "PASSPORT_APPEND_ERROR", "message": str(e)}
    except Exception as e:
        return {"status": "FAILED", "reason": "UNEXPECTED", "message": str(e)}
