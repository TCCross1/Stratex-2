"""Field-test handoff: HABITAT_PROJECTION_PATH + claim redeem (read-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "fixtures" / "habitat.projection.v1.sample.json"


@pytest.fixture()
def sample_projection(tmp_path: Path) -> Path:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    path = tmp_path / "habitat.projection.v1.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture()
def authoritative_projection(tmp_path: Path) -> Path:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["authoritative"] = True
    data["mission_id"] = "mission-sealed-official"
    path = tmp_path / "habitat.projection.v1.official.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_projection_from_env(monkeypatch, sample_projection: Path):
    from habitat_ui.projection_loader import load_projection_from_env

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(sample_projection))
    payload = load_projection_from_env()
    assert payload is not None
    assert payload["contract_id"] == "habitat.projection.v1"
    assert payload["authoritative"] is False


def test_load_projection_missing_path(monkeypatch):
    from habitat_ui.projection_loader import load_projection_from_env

    monkeypatch.delenv("HABITAT_PROJECTION_PATH", raising=False)
    assert load_projection_from_env() is None


def test_dashboard_from_file_preview(monkeypatch, sample_projection: Path):
    from habitat_ui.routes import _dashboard_from_file_or_build

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(sample_projection))
    dash = _dashboard_from_file_or_build("demo", "demo-property", stub_only=False)
    assert dash["source"] == "HABITAT_PROJECTION_PATH"
    assert dash["authoritative"] is False
    assert dash["passport_status"] == "PROJECTED"
    assert dash["property"]["address_line"] == "1234 Appalachian Way"
    assert dash["habitat_role"] == "read-only"


def test_dashboard_from_file_official(monkeypatch, authoritative_projection: Path):
    from habitat_ui.routes import _dashboard_from_file_or_build

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(authoritative_projection))
    dash = _dashboard_from_file_or_build("demo", "demo-property", stub_only=False)
    assert dash["authoritative"] is True
    assert dash["passport_status"] == "OK"
    assert dash["source"] == "HABITAT_PROJECTION_PATH"


def test_stub_only_ignores_file(monkeypatch, sample_projection: Path):
    from habitat_ui.routes import _dashboard_from_file_or_build

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(sample_projection))
    dash = _dashboard_from_file_or_build("demo", "demo-property", stub_only=True)
    assert dash["authoritative"] is False
    assert dash.get("source") != "HABITAT_PROJECTION_PATH"
    assert dash["mode"] == "demo"


def test_openings_from_file(monkeypatch, sample_projection: Path):
    from habitat_ui import routes as habitat_routes

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(sample_projection))
    out = habitat_routes.list_openings()
    assert out["source"] == "HABITAT_PROJECTION_PATH"
    assert out["authoritative"] is False
    assert len(out["openings"]) >= 2
    assert out["openings"][0]["id"] == "win-front-lr"


def test_claim_redeem_read_only(monkeypatch, sample_projection: Path):
    from habitat_ui.routes import ClaimRedeemRequest, claim_redeem

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(sample_projection))
    result = claim_redeem(
        ClaimRedeemRequest(claim_code="SH-FIELD-TEST-01", email="owner@example.com")
    )
    assert result["ok"] is True
    assert result["mode"] == "lookup"
    assert result["minted"] is False
    assert result["ledger_write"] is False
    assert result["core_publish"] is False
    assert result["habitat_role"] == "read-only"
    assert result["matched"] is True
    assert result["property_id"] == "prop-field-test-ky"
    assert result["authoritative"] is False


def test_claim_redeem_without_file(monkeypatch):
    from habitat_ui.routes import ClaimRedeemRequest, claim_redeem

    monkeypatch.delenv("HABITAT_PROJECTION_PATH", raising=False)
    result = claim_redeem(ClaimRedeemRequest(claim_code="ANY"))
    assert result["ok"] is True
    assert result["matched"] is False
    assert result["minted"] is False
    assert result["ledger_write"] is False


def test_router_endpoints_return_json(monkeypatch, sample_projection: Path):
    """Mount habitat_ui router alone — no Mongo / full server required."""
    from fastapi import FastAPI
    from habitat_ui.routes import router

    monkeypatch.setenv("HABITAT_PROJECTION_PATH", str(sample_projection))
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    r = client.get("/api/habitat/dashboard/projection")
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")
    body = r.json()
    assert body["authoritative"] is False
    assert body["source"] == "HABITAT_PROJECTION_PATH"
    assert "property" in body

    r2 = client.post(
        "/api/habitat/v1/claim/redeem",
        json={"claim_code": "SH-4820-VH-99"},
    )
    assert r2.status_code == 200
    assert "application/json" in r2.headers.get("content-type", "")
    redeem = r2.json()
    assert redeem["minted"] is False
    assert redeem["ledger_write"] is False
    assert redeem["matched"] is True
