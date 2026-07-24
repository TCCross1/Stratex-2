"""Unit and dimensional arithmetic — Decimal-only authoritative math."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Union

from .errors import DimensionalError, ParseError, UnknownInputError

NumberLike = Union[Decimal, int, str]


class Dimension(str, Enum):
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    COUNT = "count"
    BOARD_FOOT = "board_foot"
    ROOFING_SQUARE = "roofing_square"
    UNKNOWN = "unknown"


def _to_decimal(value: NumberLike, *, name: str = "value") -> Decimal:
    if value is None:
        raise UnknownInputError(name, "value is None")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise UnknownInputError(name, "boolean is not a numeric quantity")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise UnknownInputError(name, f"not a decimal-compatible number: {value!r}") from exc


def require_known(value: Optional[NumberLike], *, name: str) -> Decimal:
    """Require an explicit numeric input — never coerce None/empty to zero."""
    if value is None:
        raise UnknownInputError(name, "missing required numeric input")
    if isinstance(value, str) and not value.strip():
        raise UnknownInputError(name, "empty string is unknown, not zero")
    return _to_decimal(value, name=name)


@dataclass(frozen=True)
class Measurement:
    """Dimensioned quantity with Decimal magnitude."""

    value: Decimal
    unit: str
    dimension: Dimension

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", Decimal(self.value))

    def as_dict(self) -> dict:
        return {
            "value": str(self.value),
            "unit": self.unit,
            "dimension": self.dimension.value,
        }


@dataclass(frozen=True)
class Length:
    """Length stored canonically in decimal feet."""

    feet: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "feet", Decimal(self.feet))

    @property
    def inches(self) -> Decimal:
        return self.feet * Decimal("12")

    def to_measurement(self) -> Measurement:
        return Measurement(self.feet, "ft", Dimension.LENGTH)

    def __add__(self, other: "Length") -> "Length":
        if not isinstance(other, Length):
            raise DimensionalError("can only add Length to Length")
        return Length(self.feet + other.feet)

    def __sub__(self, other: "Length") -> "Length":
        if not isinstance(other, Length):
            raise DimensionalError("can only subtract Length from Length")
        return Length(self.feet - other.feet)

    def __mul__(self, scalar: NumberLike) -> "Length":
        return Length(self.feet * _to_decimal(scalar, name="scalar"))

    def __truediv__(self, scalar: NumberLike) -> "Length":
        d = _to_decimal(scalar, name="scalar")
        if d == 0:
            raise DimensionalError("division by zero")
        return Length(self.feet / d)


_FRACTION_RE = re.compile(
    r"""
    ^\s*
    (?:(?P<whole>\d+)\s+)?          # optional whole number before fraction
    (?P<num>\d+)\s*/\s*(?P<den>\d+)
    \s*$
    """,
    re.VERBOSE,
)

_PLAIN_NUMBER_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:'|ft|feet)?\s*$", re.I)
_INCHES_ONLY_RE = re.compile(
    r"""
    ^\s*
    (?P<whole>-?\d+)?
    (?:\s*(?P<frac>\d+\s*/\s*\d+))?
    (?:\s*(?P<dec>\.\d+))?
    \s*(?:"|in|inch|inches)
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _parse_fraction_token(token: str) -> Decimal:
    m = _FRACTION_RE.match(token.strip())
    if not m:
        raise ParseError(token, "invalid fraction")
    whole = Decimal(m.group("whole") or "0")
    num = Decimal(m.group("num"))
    den = Decimal(m.group("den"))
    if den == 0:
        raise ParseError(token, "fraction denominator is zero")
    return whole + (num / den)


def parse_feet_inches(raw: Optional[str]) -> Length:
    """Parse construction length strings into decimal feet.

    Accepted examples:
      12'           12 ft           12.5'
      12'-6"        12' 6"          12 ft 6 in
      12'-6 1/2"    6 1/2"          78"
      10' - 3-3/4"
    """
    if raw is None:
        raise UnknownInputError("length_string", "missing length string")
    if not isinstance(raw, str):
        raise ParseError(str(raw), "length input must be a string")
    text = raw.strip()
    if not text:
        raise UnknownInputError("length_string", "empty length string is unknown")

    # Normalize common separators: 12'-6-1/2" → keep feet and inch parts.
    text = text.replace("′", "'").replace("″", '"').replace("–", "-").replace("—", "-")

    # Plain decimal feet (optional ft marker).
    plain = _PLAIN_NUMBER_RE.match(text)
    if plain and "'" not in text and '"' not in text.lower() and "in" not in text.lower():
        # Bare number without unit marker is ambiguous → reject (unknown unit).
        if not re.search(r"(ft|feet|')", text, re.I):
            raise ParseError(raw, "bare number lacks length unit")
        return Length(_to_decimal(plain.group(1), name="feet"))

    # Inches-only forms.
    inches_only = _INCHES_ONLY_RE.match(text)
    if inches_only and not re.search(r"(ft|feet|')", text, re.I):
        inches = Decimal("0")
        if inches_only.group("whole"):
            inches += Decimal(inches_only.group("whole"))
        if inches_only.group("frac"):
            inches += _parse_fraction_token(inches_only.group("frac"))
        if inches_only.group("dec"):
            # Attach decimal to whole inches if present, else as fractional inches.
            if inches_only.group("whole") is None and inches_only.group("frac") is None:
                inches += Decimal("0" + inches_only.group("dec"))
            else:
                inches += Decimal("0" + inches_only.group("dec"))
        return Length(inches / Decimal("12"))

    # Combined feet + inches. Support "12'-6 1/2\"" and "12' 6-1/2\"".
    # First split on feet marker.
    feet_match = re.match(
        r"""^\s*(?P<feet>-?\d+(?:\.\d+)?)\s*(?:'|ft|feet)\s*(?P<rest>.*)$""",
        text,
        re.I | re.VERBOSE,
    )
    if feet_match:
        feet = _to_decimal(feet_match.group("feet"), name="feet")
        rest = feet_match.group("rest").strip().lstrip("-").strip()
        if not rest:
            return Length(feet)
        # Rest should be inches (with optional fraction).
        # Forms: 6" | 6 1/2" | 6-1/2" | 6.5" | 1/2"
        rest_norm = rest.replace("-", " ")
        inch_match = re.match(
            r"""
            ^\s*
            (?:(?P<whole>\d+)\s*)?
            (?:(?P<frac>\d+\s*/\s*\d+)\s*)?
            (?:(?P<dec>\.\d+)\s*)?
            (?:"|in|inch|inches)?
            \s*$
            """,
            rest_norm,
            re.I | re.VERBOSE,
        )
        if not inch_match or (
            inch_match.group("whole") is None
            and inch_match.group("frac") is None
            and inch_match.group("dec") is None
        ):
            raise ParseError(raw, f"unrecognized inches portion {rest!r}")
        inches = Decimal("0")
        if inch_match.group("whole"):
            inches += Decimal(inch_match.group("whole"))
        if inch_match.group("frac"):
            inches += _parse_fraction_token(inch_match.group("frac"))
        if inch_match.group("dec"):
            inches += Decimal("0" + inch_match.group("dec"))
        return Length(feet + inches / Decimal("12"))

    # Decimal feet with explicit marker already handled; try inches-only failed.
    raise ParseError(raw, "unrecognized feet/inches format")


def parse_length_to_feet(raw: Optional[str]) -> Decimal:
    """Convenience: parse to Decimal feet."""
    return parse_feet_inches(raw).feet


def quantize(value: Decimal, places: str = "0.000001") -> Decimal:
    """Deterministic half-up quantization for intermediate display."""
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)
