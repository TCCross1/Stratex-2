"""Smoke test the Ice & Water Shield CV pipeline against three input scenarios."""
import asyncio, os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import httpx

BASE = "http://localhost:8001"


async def get_admin_token() -> str:
    async with httpx.AsyncClient(timeout=10.0) as c:
        # tour-mode user (john) — no MFA
        r = await c.post(f"{BASE}/api/auth/login", json={
            "email": "john@crownroofing.com",
            "password": "unstoppable",
        })
        r.raise_for_status()
        return r.json()["access_token"]


def frame(*, base_conf=0.95, dt=(0.7, 1.2), straight=0.95, gravity=False, width=36.0, offset=0.5,
          ε=0.92, hours_after_sunset=4.0) -> dict:
    from datetime import datetime, timedelta, timezone
    sunset = datetime(2026, 2, 28, 23, 0, tzinfo=timezone.utc)
    return {
        "frame_id": "FR-1", "contractor_id": "C-1", "job_id": "J-1",
        "valley_track_id": "V-1",
        "capture": {
            "captured_at_utc": (sunset + timedelta(hours=hours_after_sunset)).isoformat(),
            "sunset_utc": sunset.isoformat(),
            "surface_emissivity": ε,
        },
        "delta_t_band_c": list(dt),
        "edge": {
            "straightness_score": straight,
            "follows_gravity_channels": gravity,
            "measured_band_width_in": width,
            "centerline_offset_in": offset,
        },
        "base_confidence": base_conf,
    }


async def post_frame(tok: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(f"{BASE}/api/cv/ice-shield/analyze",
                         headers={"Authorization": f"Bearer {tok}"}, json=body)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()


async def run():
    tok = await get_admin_token()
    print(f"[ok] tour-mode token acquired ({tok[:16]}…)")

    # 1) Confident I&WS present
    r = await post_frame(tok, frame())
    assert r["classification"] == "Ice_Water_Shield_Present", r
    assert r["has_ice_and_water_shield"] is True
    assert r["code_compliant_underlayment"] is True
    assert r["halted"] is False
    print(f"[ok] case 1 — I&WS confirmed (conf={r['confidence']})")

    # 2) Confident moisture anomaly (gravity-bleeding, irregular edge — valley_mask still passes)
    r = await post_frame(tok, frame(straight=0.05, gravity=True, width=36.0, offset=1.0, base_conf=0.99))
    assert r["classification"] == "Moisture_Anomaly", r
    assert r["flag_for_estimation_pipeline"] is True
    assert r["halted"] is False
    print(f"[ok] case 2 — Moisture anomaly routed (conf={r['confidence']})")

    # 3) Low-confidence → halt to Overseer
    r = await post_frame(tok, frame(base_conf=0.55, straight=0.70, width=32.0, offset=3.0))
    assert r["classification"] == "Unverified_Halt", r
    assert r["halted"] is True
    assert r["halt_payload"]["review_priority"] == "P1"
    print(f"[ok] case 3 — halted to Overseer (conf={r['confidence']})")

    # 4) Window violation → precondition fails → confidence dampened
    r = await post_frame(tok, frame(hours_after_sunset=0.5))
    failing = [p for p in r["preconditions"] if p["name"] == "post_sunset_window"]
    assert failing and not failing[0]["passed"]
    print(f"[ok] case 4 — capture window violation surfaced (conf={r['confidence']})")

    print("\nICE-SHIELD CV PIPELINE — ALL CASES PASS ✓")


if __name__ == "__main__":
    asyncio.run(run())
