import queue
import sys
import time

from camera import capture_and_save

_INTERVAL_MAP = {"interval:30s": ("30s", 30), "interval:1min": ("1min", 60), "interval:2min": ("2min", 120)}


def input_listener(cmd_queue, stop_event):
    """Daemon thread — reads stdin and puts commands onto cmd_queue."""
    while not stop_event.is_set():
        try:
            line = sys.stdin.readline()
            if not line:  # EOF / pipe closed
                break
            cmd = line.strip().lower()
            if cmd:
                cmd_queue.put(cmd)
        except Exception:
            break


def interruptible_sleep(seconds, cmd_queue, stop_event, unit_state=None):
    """
    Sleeps for `seconds` while processing commands as they arrive.
      snap              — immediate capture, schedule unaffected
      interval:<value>  — updates unit_state, takes effect next cycle
      quit/stop/exit/q  — returns 'quit'
    Returns 'quit' if an exit command is received, otherwise None.
    """
    deadline = time.time() + seconds
    while time.time() < deadline:
        if stop_event.is_set():
            return "quit"
        try:
            cmd = cmd_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if cmd in ("quit", "stop", "exit", "q"):
            return "quit"
        elif cmd == "snap":
            print("--- On-demand capture ---")
            capture_and_save("on_demand")
        elif cmd in _INTERVAL_MAP and unit_state is not None:
            label, secs = _INTERVAL_MAP[cmd]
            unit_state["interval"]      = label
            unit_state["interval_secs"] = secs
            print(f"Interval updated to {label}")
        else:
            print(f"Unknown command '{cmd}'. Commands: snap, quit, interval:30s/1min/2min")
    return None
