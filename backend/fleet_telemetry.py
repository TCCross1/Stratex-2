# backend/fleet_telemetry.py
# STRATEX HARDWARE GATEWAY - TELEMETRY INGRESS

import json
import logging
import os

MASTER_DATA_FOLDER = "Stratex_Master_Data"
if not os.path.exists(MASTER_DATA_FOLDER):
    os.makedirs(MASTER_DATA_FOLDER)

logger = logging.getLogger("StratexTelemetry")

def ingest_drone_data(telemetry_packet: dict):
    """Directly bridges DJI Manifold 3 data to the Stratex core."""
    if telemetry_packet.get("hardware_sync_status") != "ACTIVE":
        return {"status": "ERROR", "message": "Hardware handshake failed"}

    if telemetry_packet.get("accuracy_score", 0) < 0.95:
        return {"status": "SIGNAL_RESCAN", "message": "Precision below standards"}

    job_id = telemetry_packet.get("job_id", "unknown_job")
    filepath = f"{MASTER_DATA_FOLDER}/{job_id}_telemetry.json"
    
    with open(filepath, 'w') as f:
        json.dump(telemetry_packet, f)
        
    from core import process_master_data_ingress
    return process_master_data_ingress(telemetry_packet)
