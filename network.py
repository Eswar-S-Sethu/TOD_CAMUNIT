import requests

from config import UPLOAD_URL


def upload_payload(payload):
    """POSTs a payload dict to UPLOAD_URL. Returns True on HTTP 200."""
    try:
        response = requests.post(UPLOAD_URL, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Warning: Upload failed ({e})")
        return False
