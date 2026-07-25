"""RT-003 structured observability helpers — safe logs and metrics.

Never emit secrets, tokens, connection strings, or customer payload bodies.
Lane 5 runtime/QE foundation only — no Passport/ATC/Estimator/Habitat authority.
Production readiness: NOT READY.
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence

# Keys that must never appear in log/metric attribute values.
SECRET_KEY_FRAGMENTS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "hmac_key",
        "hmac",
        "totp",
        "mfa",
        "private_key",
        "access_key",
        "secret_key",
        "credential",
        "mongo_url",
        "database_url",
        "connection_string",
    }
)

# Attribute keys that look like customer/PII payload carriers.
CUSTOMER_PAYLOAD_KEYS = frozenset(
    {
        "payload",
        "customer_payload",
        "body",
        "raw_body",
        "request_body",
        "response_body",
        "email",
        "phone",
        "ssn",
        "address",
        "full_name",
        "customer_name",
        "homeowner_name",
        "photo_bytes",
        "image_bytes",
        "file_bytes",
        "object_url",
        "presigned_url",
        "signed_url",
        "tenant_id",
        "property_id",
        "contractor_margin",
        "wholesale_cost",
        "internal_cost",
        "markup",
        "commission",
        "profit",
    }
)

# High-cardinality identifiers must never become global metric labels.
HIGH_CARDINALITY_LABEL_KEYS = frozenset(
    {
        "tenant_id",
        "property_id",
        "passport_id",
        "report_publication_id",
        "event_id",
        "user_id",
        "actor_id",
        "object_url",
        "presigned_url",
    }
)

EXCEPTION_TEXT_MAX_CHARS = 240

_REDACTED = "[REDACTED]"
_CONN_CRED_RE = re.compile(r"(://)([^/\s:@]+):([^@/\s]+)(@)")


def _key_is_sensitive(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if normalized in SECRET_KEY_FRAGMENTS or normalized in CUSTOMER_PAYLOAD_KEYS:
        return True
    return any(frag in normalized for frag in SECRET_KEY_FRAGMENTS)


def bound_exception_text(exc: Any) -> str:
    """Bound exception text for telemetry — never dump full payloads."""
    text = str(exc)
    if len(text) > EXCEPTION_TEXT_MAX_CHARS:
        return text[:EXCEPTION_TEXT_MAX_CHARS] + "...[truncated]"
    return text


def scrub_for_log(value: Any, *, _depth: int = 0) -> Any:
    """Return a JSON-safe structure with secrets/customer payloads removed."""
    if _depth > 6:
        return "[TRUNCATED_DEPTH]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, BaseException):
        return bound_exception_text(value)
    if isinstance(value, str):
        if "://" in value and "@" in value:
            return _CONN_CRED_RE.sub(r"\1***:***\4", value)
        # Credential-bearing or signed object URLs without userinfo.
        lower = value.lower()
        if "://" in value and any(
            marker in lower
            for marker in (
                "x-amz-signature=",
                "x-amz-credential=",
                "signature=",
                "access_key",
                "token=",
            )
        ):
            return _REDACTED
        if len(value) > 512:
            return value[:128] + f"...[truncated len={len(value)}]"
        return value
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if _key_is_sensitive(key):
                out[key] = _REDACTED
            else:
                out[key] = scrub_for_log(v, _depth=_depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [scrub_for_log(v, _depth=_depth + 1) for v in value[:50]]
    # Bytes / unknown objects — never dump raw content.
    if isinstance(value, (bytes, bytearray)):
        return f"[BYTES len={len(value)}]"
    return str(type(value).__name__)


@dataclass
class SafeLogger:
    """Structured JSON logger that refuses secret/customer payload attributes."""

    name: str = "stratex.rt003"
    production_readiness: str = "NOT_READY"
    _logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_logger", logging.getLogger(self.name))

    def _emit(self, level: int, event: str, **attrs: Any) -> str:
        safe_attrs = scrub_for_log(attrs)
        if not isinstance(safe_attrs, dict):
            safe_attrs = {"attrs": safe_attrs}
        record = {
            "event": str(event),
            "production_readiness": self.production_readiness,
            "attrs": safe_attrs,
            "ts_ms": int(time.time() * 1000),
        }
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        self._logger.log(level, line)
        return line

    def info(self, event: str, **attrs: Any) -> str:
        return self._emit(logging.INFO, event, **attrs)

    def warning(self, event: str, **attrs: Any) -> str:
        return self._emit(logging.WARNING, event, **attrs)

    def error(self, event: str, **attrs: Any) -> str:
        return self._emit(logging.ERROR, event, **attrs)


@dataclass
class MetricSample:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class SafeMetrics:
    """In-process counters/timers with label allowlists only.

    Labels are restricted to short alphanumeric tokens — never free-form payloads.
    """

    allowed_label_keys: Sequence[str] = (
        "component",
        "operation",
        "outcome",
        "marker",
    )
    _counters: MutableMapping[str, float] = field(default_factory=lambda: defaultdict(float))
    _timings_ms: MutableMapping[str, list] = field(default_factory=lambda: defaultdict(list))

    def _sanitize_labels(self, labels: Optional[Mapping[str, Any]]) -> Dict[str, str]:
        allowed = set(self.allowed_label_keys)
        clean: Dict[str, str] = {}
        for k, v in (labels or {}).items():
            key = str(k)
            if key in HIGH_CARDINALITY_LABEL_KEYS:
                continue
            if key not in allowed:
                continue
            if _key_is_sensitive(key):
                continue
            text = str(v)
            if len(text) > 64:
                text = text[:64]
            if not re.fullmatch(r"[A-Za-z0-9_.:\-]+", text):
                text = "invalid_label"
            clean[key] = text
        return clean

    def incr(self, name: str, value: float = 1.0, labels: Optional[Mapping[str, Any]] = None) -> MetricSample:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,64}", name):
            raise ValueError(f"invalid metric name: {name!r}")
        if value < 0:
            raise ValueError("counter increments must be non-negative")
        labs = self._sanitize_labels(labels)
        key = name + "|" + json.dumps(labs, sort_keys=True, separators=(",", ":"))
        self._counters[key] += float(value)
        return MetricSample(name=name, value=self._counters[key], labels=labs)

    def observe_ms(self, name: str, duration_ms: float, labels: Optional[Mapping[str, Any]] = None) -> MetricSample:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,64}", name):
            raise ValueError(f"invalid metric name: {name!r}")
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        labs = self._sanitize_labels(labels)
        key = name + "|" + json.dumps(labs, sort_keys=True, separators=(",", ":"))
        bucket = self._timings_ms[key]
        bucket.append(float(duration_ms))
        # Bound memory in CI — keep last 256 samples per series.
        if len(bucket) > 256:
            del bucket[:-256]
        return MetricSample(name=name, value=float(duration_ms), labels=labs)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "production_readiness": "NOT_READY",
            "counters": dict(self._counters),
            "timings_ms": {k: list(v) for k, v in self._timings_ms.items()},
        }
