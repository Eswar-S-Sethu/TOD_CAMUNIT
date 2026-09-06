"""
Structured 4-stream logging for the camera unit.

Streams:
  capture      → logs/camunit_capture_log.txt
  transmission → logs/payload_transmission_log.txt
  crash        → logs/crashes_log.txt
  unexpected   → logs/unexpected_events_log.txt

All entries are also printed to stdout to preserve the existing visible output.
Entry format: [YYYY-MM-DD HH:MM:SS] [LEVEL] message
"""
import threading
import traceback
from datetime import datetime

from config import LOGS_DIR

LOGS_DIR.mkdir(exist_ok=True)

_CAPTURE_LOG      = LOGS_DIR / "camunit_capture_log.txt"
_TRANSMISSION_LOG = LOGS_DIR / "payload_transmission_log.txt"
_CRASH_LOG        = LOGS_DIR / "crashes_log.txt"
_UNEXPECTED_LOG   = LOGS_DIR / "unexpected_events_log.txt"

_capture_lock      = threading.Lock()
_transmission_lock = threading.Lock()
_crash_lock        = threading.Lock()
_unexpected_lock   = threading.Lock()


def _write(path, lock, level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level}] {msg}\n"
    with lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
    print(entry, end="")


def log_capture(level, msg):
    """Log a capture-related event (face detection, retry, discard, error)."""
    _write(_CAPTURE_LOG, _capture_lock, level, msg)


def log_transmission(level, msg):
    """Log a payload or snapshot transmission event (upload, retry, failure)."""
    _write(_TRANSMISSION_LOG, _transmission_lock, level, msg)


def log_crash(msg):
    """Log an unhandled exception with its traceback."""
    _write(_CRASH_LOG, _crash_lock, "CRASH", msg)


def log_unexpected(level, msg):
    """Log an unexpected or anomalous event (unknown commands, model errors, etc.)."""
    _write(_UNEXPECTED_LOG, _unexpected_lock, level, msg)
