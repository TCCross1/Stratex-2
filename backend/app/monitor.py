import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StratexProcessor")

def parse_diagnostic_file(file_path):
    logger.info(f"🔍 Parsing: {file_path.name}")
    
    data = {"source": file_path.name, "devices": []}
    
    with open(file_path, 'r') as f:
        for line in f:
            if "VID:" in line and "PID:" in line:
                # Extracts the hex codes for your hardware
                parts = line.split()
                data["devices"].append({"vid": parts[1], "pid": parts[3]})
    
    # Save the cleaned result to our 'processed' folder
    output_path = Path("/app/backend/app/data/processed") / f"{file_path.stem}_clean.json"
    with open(output_path, 'w') as out_f:
        json.dump(data, out_f, indent=4)
        
    logger.info(f"✅ Data cleaned and saved to: {output_path.name}")

if __name__ == "__main__":
    # You can run this to manually test it
    test_file = Path("/app/backend/app/data/raw/updd.raw.txt")
    if test_file.exists():
        parse_diagnostic_file(test_file)
