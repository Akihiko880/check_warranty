import json
import os
import csv
from datetime import datetime
from config.settings import RESULTS_CSV, CHECKPOINT_FILE

def get_timestamp() -> str:
    return datetime.now().isoformat()

def chunk_list(items: list, size: int):
    for i in range(0, len(items), size):
        yield {
            "batch_id": i // size,
            "start_idx": i,
            "end_idx": min(i + size - 1, len(items) - 1),
            "imeis": items[i:i+size]
        }

def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_checkpoint(data: dict):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_to_csv(log_entry: dict):
    fieldnames = ["timestamp", "website", "imei", "status", "reason", "result_snippet"]
    file_exists = os.path.isfile(RESULTS_CSV)
    
    # Làm sạch dữ liệu string trước khi ghi
    for key in log_entry:
        if isinstance(log_entry[key], str):
            log_entry[key] = log_entry[key].replace('\n', ' ').replace('\r', ' ').strip()

    with open(RESULTS_CSV, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)