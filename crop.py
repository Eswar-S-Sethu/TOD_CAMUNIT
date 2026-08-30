import json
import threading
from pathlib import Path

from config import STORAGE_DIR

CROP_FILE = STORAGE_DIR / "crop.json"

_lock = threading.Lock()
_crop = None  # None = full frame; dict with x, y, w, h (frame pixel coords)


def load_crop():
    """Loads a saved crop region from disk on startup."""
    global _crop
    if CROP_FILE.exists():
        with _lock:
            _crop = json.loads(CROP_FILE.read_text())


def get_crop():
    """Returns the current crop region dict, or None if full frame is active."""
    with _lock:
        return dict(_crop) if _crop else None


def set_crop(x, y, w, h):
    """Sets and persists a new crop region."""
    global _crop
    region = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
    with _lock:
        _crop = region
    CROP_FILE.write_text(json.dumps(region, indent=4))


def clear_crop():
    """Removes the crop region, reverting to full frame."""
    global _crop
    with _lock:
        _crop = None
    CROP_FILE.unlink(missing_ok=True)


def apply_crop(frame):
    """
    Applies the current crop region to a frame.
    Returns the original frame unchanged if no crop is set.
    Clamps the region to frame dimensions to guard against stale values.
    """
    region = get_crop()
    if region is None:
        return frame
    fh, fw = frame.shape[:2]
    x = max(0, min(region["x"], fw))
    y = max(0, min(region["y"], fh))
    w = max(1, min(region["w"], fw - x))
    h = max(1, min(region["h"], fh - y))
    return frame[y:y + h, x:x + w]
