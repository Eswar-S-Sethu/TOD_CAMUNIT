import json
from datetime import datetime

from config import MAX_STORAGE_BYTES, STORAGE_DIR, UPLOADED_LOG
from logger import log_capture, log_transmission
from network import upload_payload


# ── Internal helpers ───────────────────────────────────────────────────────────

def _capture_files():
    """Returns all capture JSON files sorted oldest-first."""
    return sorted(STORAGE_DIR.glob("capture_*.json"))


def _load_uploaded_set():
    """Returns the set of filenames that have been successfully uploaded."""
    if not UPLOADED_LOG.exists():
        return set()
    return set(UPLOADED_LOG.read_text().splitlines())


def _save_uploaded_set(uploaded):
    """Persists the uploaded set, pruning entries for files that no longer exist."""
    existing = {f.name for f in _capture_files()}
    UPLOADED_LOG.write_text("\n".join(sorted(uploaded & existing)))


def _enforce_storage_limit():
    """Delete the oldest captures until total storage is under MAX_STORAGE_BYTES."""
    files = _capture_files()
    total = sum(f.stat().st_size for f in files)
    if total <= MAX_STORAGE_BYTES:
        return
    uploaded = _load_uploaded_set()
    for f in files:
        if total <= MAX_STORAGE_BYTES:
            break
        total -= f.stat().st_size
        uploaded.discard(f.name)
        f.unlink()
    _save_uploaded_set(uploaded)


# ── Public API ─────────────────────────────────────────────────────────────────

def save_locally(payload, label):
    """
    Always saves payload to the local rolling store (regardless of upload outcome).
    Enforces the 10 GB cap by evicting the oldest files when needed.
    Returns the saved Path.
    """
    STORAGE_DIR.mkdir(exist_ok=True)
    filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{label}.json"
    filepath = STORAGE_DIR / filename
    filepath.write_text(json.dumps(payload, indent=4))
    _enforce_storage_limit()
    log_capture("INFO", f"Saved locally: {filename}")
    return filepath


def mark_as_uploaded(filename):
    """Records a capture filename as successfully uploaded."""
    uploaded = _load_uploaded_set()
    uploaded.add(filename)
    _save_uploaded_set(uploaded)


def retry_pending_uploads():
    """Uploads any locally stored captures not yet successfully uploaded."""
    all_files = _capture_files()
    uploaded = _load_uploaded_set()
    pending = [f for f in all_files if f.name not in uploaded]
    if not pending:
        return
    print(f"Retrying {len(pending)} pending upload(s)...")
    for filepath in pending:
        try:
            payload = json.loads(filepath.read_text())
            if upload_payload(payload):
                uploaded.add(filepath.name)
                log_transmission("INFO", f"Retry upload succeeded: {filepath.name}")
            else:
                log_transmission("WARN", f"Retry upload failed: {filepath.name}")
        except Exception as e:
            log_transmission("WARN", f"Retry error for {filepath.name}: {e}")
    _save_uploaded_set(uploaded)
