import argparse
import queue
import threading

from camera import capture_and_save
from camera_manager import camera as cam
from commands import input_listener, interruptible_sleep
from config import STORAGE_DIR
from crop import load_crop
from location import get_location, load_location
from render_client import start_render_client
from storage import retry_pending_uploads

_INTERVAL_MAP = {"30s": 30, "1min": 60, "2min": 120}


def parse_args():
    parser = argparse.ArgumentParser(description="TOD Camera Unit")
    parser.add_argument(
        "--interval",
        choices=["30s", "1min", "2min"],
        required=True,
        help="Capture interval: 30s, 1min, or 2min",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    STORAGE_DIR.mkdir(exist_ok=True)
    load_crop()      # Restore any saved crop region from disk
    load_location()  # Restore any saved location override from disk

    # Shared mutable state — updated by render_client and commands
    unit_state = {
        "interval":      args.interval,
        "interval_secs": _INTERVAL_MAP[args.interval],
        "location":      get_location(),
    }

    print(f"\nCamera unit starting — interval: {args.interval} | location: {get_location()}")
    print("Commands: 'snap' | 'quit' | 'interval:30s' | 'interval:1min' | 'interval:2min'\n")

    cam.start()   # Begin continuous background camera read loop

    stop_event = threading.Event()
    cmd_queue  = queue.Queue()

    threading.Thread(
        target=input_listener, args=(cmd_queue, stop_event), daemon=True
    ).start()

    start_render_client(cmd_queue, stop_event, unit_state)

    while not stop_event.is_set():
        # Drain commands queued since last cycle
        while not cmd_queue.empty():
            try:
                cmd = cmd_queue.get_nowait()
            except queue.Empty:
                break
            if cmd in ("quit", "stop", "exit", "q"):
                stop_event.set()
                break
            elif cmd == "snap":
                print("--- On-demand capture ---")
                capture_and_save("on_demand")
            elif cmd in ("interval:30s", "interval:1min", "interval:2min"):
                label = cmd.split(":")[1]
                unit_state["interval"]      = label
                unit_state["interval_secs"] = _INTERVAL_MAP[label]
                print(f"Interval updated to {label}")
            else:
                print(f"Unknown command '{cmd}'.")

        if stop_event.is_set():
            break

        retry_pending_uploads()

        capture_and_save("start_of_interval")

        wait = unit_state["interval_secs"] - 2
        if interruptible_sleep(wait, cmd_queue, stop_event, unit_state) == "quit":
            break

        capture_and_save("end_of_interval")

        if interruptible_sleep(2, cmd_queue, stop_event, unit_state) == "quit":
            break

    stop_event.set()
    cam.stop()
    print("Program shut down cleanly.")


if __name__ == "__main__":
    main()
