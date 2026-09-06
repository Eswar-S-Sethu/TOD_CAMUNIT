import requests

from config import UPLOAD_URL
from logger import log_transmission


def upload_payload(payload):
    """POSTs a payload dict to UPLOAD_URL. Returns True on HTTP 200."""
    timestamp = payload.get("timestamp", "unknown")
    label     = payload.get("timing_label", "unknown")
    try:
        response = requests.post(UPLOAD_URL, json=payload, timeout=10)
        if response.status_code == 200:
            log_transmission("INFO", f"Uploaded payload [{label}] @ {timestamp} → {UPLOAD_URL}")
            return True
        log_transmission("WARN", f"Upload rejected (HTTP {response.status_code}) [{label}] @ {timestamp}")
        return False
    except Exception as e:
        log_transmission("WARN", f"Upload failed [{label}] @ {timestamp}: {e}")
        return False
