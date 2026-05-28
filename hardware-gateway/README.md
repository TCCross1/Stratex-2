# STRATEX™ Local Hardware Gateway

This directory holds the **on-site** Node.js gateway that runs on the tablet /
dock controller alongside the drone trailer. It is **not** part of the SaaS
backend deployment — the cloud backend ships a wire-compatible simulator at
`ws(s)://<REACT_APP_BACKEND_URL>/api/ws/stratex/core?token=<jwt>` so the same
React Fleet Launch dashboard works against both.

## Wire Protocol

### Telemetry frames (gateway → UI, 4 Hz)

```json
{
  "dock":        { "hatch_status": "OPEN|CLOSED", "perimeter_clear": true, "internal_temp_c": 21.0 },
  "drone":       { "battery_percent": 100, "gps_status": "POSITION_OK_FIXED", "signal_rssi": 94 },
  "environment": { "wind_speed_mph": 3.4, "is_raining": false }
}
```

The cloud simulator additionally emits:

```json
{ "event": "MISSION_LAUNCHED", "job_id": "...", "authorization_id": "...", "server_timestamp": "..." }
```

after a successful launch authorization.

### Commands (UI → gateway)

```json
{
  "command":  "AUTHORIZE_FLEET_LAUNCH",
  "timestamp": 1737499200000,
  "payload":   { "project_id": "PRJ-2026-X", "approved_value": "$41,298.36", "job_id": "<optional uuid>" }
}
```

## Install / Run (on-site only)

```bash
cd /app/hardware-gateway
npm install ws serialport @serialport/parser-readline
node stratex-gateway.js
```

The gateway binds `localhost:8080`. Point the dashboard at it with:

```
REACT_APP_BACKEND_URL=http://localhost:8080      # OR keep cloud and toggle in UI
```

Serial path defaults to `/dev/ttyUSB0` (Linux/macOS) — update to `COM3` on Windows.
