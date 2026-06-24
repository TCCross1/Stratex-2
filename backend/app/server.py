@app.get("/api/stratex-quant/scans")
async def get_scan_results():
    processed_dir = "/app/backend/app/data/processed"
    results = []
    
    for filename in os.listdir(processed_dir):
        if filename.endswith("_quant.json"): # Only grab Stratex structural scans
            with open(os.path.join(processed_dir, filename), 'r') as f:
                results.append(json.load(f))
                
    return {"project": "Stratex-Quant", "scans": results}
