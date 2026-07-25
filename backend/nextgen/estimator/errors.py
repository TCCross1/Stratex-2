"""Estimator math error types — unknown inputs never silently zero-fill."""
from __future__ import annotations


class EstimatorMathError(ValueError):
    """Base error for Construction Math Engine failures."""


class UnknownInputError(EstimatorMathError):
    """Raised when a required input is missing or explicitly unknown.

    Constitutional rule: no silent zero-fill of missing quantities.
    """

    def __init__(self, input_name: str, detail: str | None = None) -> None:
        self.input_name = input_name
        self.detail = detail
        msg = f"unknown_input:{input_name}"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


class DimensionalError(EstimatorMathError):
    """Raised when units or dimensions are incompatible."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"dimensional_error: {detail}")


class ParseError(EstimatorMathError):
    """Raised when a feet/inches/fraction string cannot be parsed."""

    def __init__(self, raw: str, detail: str | None = None) -> None:
        self.raw = raw
        self.detail = detail
        msg = f"parse_error: cannot parse length {raw!r}"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


class LedgerReplayError(EstimatorMathError):
    """Controlled integrity failure during executable ledger replay."""

    def __init__(self, detail: str, *, code: str = "REPLAY_INTEGRITY") -> None:
        self.detail = detail
        self.code = code
        super().__init__(f"ledger_replay_error:{code}: {detail}")


class LedgerReplayMismatch(LedgerReplayError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, code="REPLAY_MISMATCH")


class LedgerReplayVersionMissing(LedgerReplayError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, code="REPLAY_VERSION_MISSING")
