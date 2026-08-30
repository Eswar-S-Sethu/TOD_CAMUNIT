import json
import threading

from config import LOCATION_NAME, STORAGE_DIR

_LOCATION_FILE = STORAGE_DIR / "location.json"

_lock     = threading.Lock()
_location = None  # None = use config.py default


def load_location():
    """Loads a saved location override from disk on startup."""
    global _location
    if _LOCATION_FILE.exists():
        with _lock:
            data = json.loads(_LOCATION_FILE.read_text())
            _location = data if isinstance(data, str) else None


def get_location():
    """Returns the current location name (persisted override or config default)."""
    with _lock:
        return _location if _location else LOCATION_NAME


def set_location(name):
    """Sets and persists a new location name to disk."""
    global _location
    with _lock:
        _location = name
    _LOCATION_FILE.write_text(json.dumps(name))
