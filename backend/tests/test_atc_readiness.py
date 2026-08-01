"""Unit tests for ATC Readiness Gate — Field Test v1"""

from backend.nextgen.atc.readiness import evaluate_readiness


def test_all_checks_pass():
    r = evaluate_readiness("m1", battery_pct=80.0)
    assert r.ready is True
    assert r.blocking_failures == []


def test_low_battery_blocks():
    r = evaluate_readiness("m2", battery_pct=25.0)
    assert r.ready is False
    assert "battery" in r.blocking_failures


def test_pilot_not_authorized_blocks():
    r = evaluate_readiness("m3", pilot_authorized=False)
    assert r.ready is False
    assert "pilot_authorization" in r.blocking_failures


def test_multiple_failures():
    r = evaluate_readiness(
        "m4",
        weather_ok=False,
        rtk_ready=False,
        battery_pct=10.0,
    )
    assert r.ready is False
    assert set(r.blocking_failures) >= {"weather", "rtk", "battery"}
