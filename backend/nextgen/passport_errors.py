"""Controlled Passport append / conflict / idempotency errors (C-P-002)."""
from __future__ import annotations

from typing import Any, Dict, Optional


class PassportAppendError(Exception):
    """Base for governed append failures that are not unexpected crashes."""

    code: str = "PASSPORT_APPEND_FAILED"

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MissingExpectedStateError(PassportAppendError):
    code = "MISSING_EXPECTED_STATE"


class StaleExpectedStateError(PassportAppendError):
    code = "STALE_EXPECTED_STATE"

    def __init__(self, message: str, *, conflict: Dict[str, Any], details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.conflict = conflict


class IdempotencyConflictError(PassportAppendError):
    code = "IDEMPOTENCY_CONFLICT"


class TransactionUnavailableError(PassportAppendError):
    code = "TRANSACTION_UNAVAILABLE"


class SealRequiredError(PassportAppendError):
    code = "SEAL_REQUIRED"


class TenantIsolationError(PassportAppendError):
    code = "TENANT_ISOLATION"


class PropertyIsolationError(PassportAppendError):
    code = "PROPERTY_ISOLATION"
