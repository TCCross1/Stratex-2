"""Smoke test the Fleet Launch WS simulator. Run from /app/backend after `source .env`."""
import asyncio
import json
import os
import sys
from pathlib import Path

# explicit env load — never trust the subshell
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import websockets  # noqa: E402
import httpx       # noqa: E402

BASE = "http://localhost:8001"
WS   = "ws://localhost:8001/api/ws/stratex/core"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASS  = "StratexAdmin!2026"


async def login_admin() -> str:
    async with httpx.AsyncClient(timeout=10.0) as c:
        # fetch current TOTP via demo bypass endpoint
        r0 = await c.get(f"{BASE}/api/auth/totp-debug", params={"email": ADMIN_EMAIL})
        r0.raise_for_status()
        totp_code = r0.json()["current_code"]

        r2 = await c.post(f"{BASE}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASS,
            "totp_code": totp_code,
        })
        r2.raise_for_status()
        return r2.json()["access_token"]


async def run():
    tok = await login_admin()
    print(f"[ok] admin token acquired ({tok[:18]}…)")

    url = f"{WS}?token={tok}"
    async with websockets.connect(url) as ws:
        # collect frames until ready (or timeout 15s)
        ready = False
        last = None
        for _ in range(60):
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            if msg.get("event") == "HELLO":
                print(f"[ok] HELLO from {msg.get('source')} schema {msg.get('schema_version')}")
                continue
            if msg.get("dock") and msg.get("drone"):
                last = msg
                d, dr, env = msg["dock"], msg["drone"], msg["environment"]
                if (
                    d["hatch_status"] == "OPEN"
                    and d["perimeter_clear"]
                    and dr["battery_percent"] >= 100
                    and dr["gps_status"] == "POSITION_OK_FIXED"
                    and dr["signal_rssi"] >= 75
                    and env["wind_speed_mph"] < 5
                    and not env["is_raining"]
                ):
                    ready = True
                    print(f"[ok] frame green: hatch={d['hatch_status']} batt={dr['battery_percent']}% gps={dr['gps_status']} rssi={dr['signal_rssi']}")
                    break
        assert ready, f"never converged to green; last frame: {last}"

        # send authorize
        await ws.send(json.dumps({
            "command": "AUTHORIZE_FLEET_LAUNCH",
            "timestamp": 0,
            "payload": {"project_id": "PRJ-TEST", "approved_value": "$1.00", "job_id": None},
        }))

        # wait for MISSION_LAUNCHED
        for _ in range(20):
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            msg = json.loads(raw)
            if msg.get("event") == "MISSION_LAUNCHED":
                print(f"[ok] MISSION_LAUNCHED id={msg['authorization_id']} job_updated={msg['job_status_updated']}")
                break
            if msg.get("event") == "AUTH_REJECTED":
                print(f"[FAIL] AUTH_REJECTED: {msg}")
                sys.exit(1)
        else:
            print("[FAIL] no MISSION_LAUNCHED received")
            sys.exit(1)

    # confirm persistence
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(f"{BASE}/api/flight-authorizations/recent", headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        data = r.json()
        assert data["count"] >= 1, data
        assert data["items"][0]["project_id"] == "PRJ-TEST"
        print(f"[ok] persisted — {data['count']} total, newest project_id={data['items'][0]['project_id']}")

    print("\nALL FLEET-LAUNCH SMOKE TESTS PASSED ✓")


if __name__ == "__main__":
    asyncio.run(run())
