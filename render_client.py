import threading
from datetime import datetime

import requests

from camera import take_snapshot
from config import LOCATION_NAME, POLL_INTERVAL, RENDER_URL, UNIT_ID
from crop import clear_crop, get_crop, set_crop
from health import get_health_stats
from location import set_location as persist_location


def _register(unit_state):
    """Announces this unit to the Render dashboard on startup."""
    try:
        requests.post(
            f"{RENDER_URL}/api/units/register",
            json={
                "id": UNIT_ID,
                "location": unit_state.get("location", LOCATION_NAME),
                "config": {"crop": get_crop()},
            },
            timeout=10,
        )
        print(f"Registered with Render dashboard as '{UNIT_ID}'")
    except Exception as e:
        print(f"Warning: Could not register with Render ({e})")


def _send_snapshot():
    """Takes a preview snapshot and POSTs it to the Render dashboard."""
    img_b64, width, height = take_snapshot()
    if img_b64 is None:
        print("Warning: Snapshot requested but no frame available.")
        return
    try:
        requests.post(
            f"{RENDER_URL}/api/units/{UNIT_ID}/snapshot",
            json={
                "image_base64": img_b64,
                "width": width,
                "height": height,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            timeout=15,
        )
    except Exception as e:
        print(f"Warning: Could not send snapshot to Render ({e})")


def _process_commands(commands, cmd_queue, unit_state):
    """Applies commands received from the Render dashboard."""
    for cmd in commands:
        cmd_type = cmd.get("type")

        if cmd_type == "request_snapshot":
            _send_snapshot()

        elif cmd_type == "set_crop":
            d = cmd.get("data", {})
            set_crop(d["x"], d["y"], d["w"], d["h"])
            print(f"Crop updated from dashboard: {d}")

        elif cmd_type == "clear_crop":
            clear_crop()
            print("Crop cleared from dashboard.")

        elif cmd_type == "set_interval":
            interval = cmd.get("interval")
            mapping = {"30s": 30, "1min": 60, "2min": 120}
            if interval in mapping:
                unit_state["interval"]      = interval
                unit_state["interval_secs"] = mapping[interval]
                print(f"Interval updated from dashboard: {interval}")

        elif cmd_type == "set_location":
            location = cmd.get("location", "").strip()
            if location:
                unit_state["location"] = location
                persist_location(location)
                print(f"Location updated from dashboard: {location}")

        elif cmd_type == "snap":
            cmd_queue.put("snap")

        elif cmd_type == "stop":
            cmd_queue.put("quit")


def _poll(cmd_queue, unit_state):
    """Polls Render for pending commands and reports current state."""
    try:
        response = requests.post(
            f"{RENDER_URL}/api/units/{UNIT_ID}/poll",
            json={
                "location": unit_state.get("location"),
                "config": {
                    "interval": unit_state.get("interval"),
                    "crop": get_crop(),
                },
                "health": get_health_stats(),
            },
            timeout=5,
        )
        if response.status_code == 200:
            commands = response.json().get("commands", [])
            if commands:
                _process_commands(commands, cmd_queue, unit_state)
    except Exception as e:
        print(f"Warning: Poll to Render failed ({e})")


def start_render_client(cmd_queue, stop_event, unit_state):
    """Starts the Render polling client in a daemon thread."""
    def run():
        _register(unit_state)
        while not stop_event.is_set():
            _poll(cmd_queue, unit_state)
            stop_event.wait(POLL_INTERVAL)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    print(f"Render client started — polling every {POLL_INTERVAL}s")
