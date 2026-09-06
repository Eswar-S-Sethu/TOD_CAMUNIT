# TOD Camera Unit

A modular camera unit that captures images at a configurable interval, performs face detection to protect privacy, and uploads captures to the TOD media server. All captures are stored locally as a rolling 10 GB archive. A web dashboard hosted on Render lets you monitor units, request snapshots, set crop regions, change settings, manage WiFi connections, and put units in standby — all remotely.

---

## Requirements

- Python 3.12
- A connected webcam
- Network access to the media server at `https://tod.eswarsethu.dev`
- A deployed Render dashboard (see below)
- `nmcli` (NetworkManager CLI) for WiFi management — standard on Raspberry Pi OS (Bookworm) and Ubuntu

---

## Setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**2. Install dependencies**

```bash
pip install opencv-python requests psutil
```

**3. Configure `config.py`**

| Constant | Default | What to set |
|----------|---------|-------------|
| `UNIT_ID` | `"cam-unit-01"` | Unique ID for this camera unit — change per device |
| `LOCATION_NAME` | `"Front Door Entrance"` | Human-readable label |
| `RENDER_URL` | `"https://tod-central-dashboard.onrender.com"` | URL of the Render dashboard |
| `UPLOAD_URL` | `"https://tod.eswarsethu.dev/api/upload"` | Media server upload endpoint |
| `POLL_INTERVAL` | `5` | Seconds between dashboard polls |

---

## Running

`--interval` is required. Choose from `30s`, `1min`, or `2min`.

```bash
python main.py --interval 30s
python main.py --interval 1min
python main.py --interval 2min
```

**Example output:**

```
Camera unit starting — interval: 1min | location: Front Door Entrance
Commands: 'snap' | 'quit' | 'standby' | 'resume' | 'interval:30s' | 'interval:1min' | 'interval:2min'
```

On first run, the face detection model is automatically downloaded to `models/` (~5 MB). The `logs/` directory is also created automatically.

---

## Running as a system service

The unit is designed to run as a systemd service. The service file `tod-camunit.service` is included in the repo.

**Install (once):**

```bash
sudo cp tod-camunit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tod-camunit
```

**Start / stop / restart:**

```bash
sudo systemctl start tod-camunit
sudo systemctl stop tod-camunit
sudo systemctl restart tod-camunit
```

**Check status:**

```bash
sudo systemctl status tod-camunit
```

**Live logs:**

```bash
journalctl -u tod-camunit -f
```

The default interval is `30s` and is set in the `ExecStart` line of `tod-camunit.service`. Stdin commands are not available in service mode — use the dashboard instead.

---

## How it works

### Capture cycle

Each cycle captures two photos — one at the start and one near the end of the interval — then repeats. Before saving any frame, face detection runs and will retry up to 3 times (with a 5-second gap) if a face is detected. Captures are skipped entirely while the unit is in standby.

```
loop:
  drain stdin commands (snap / quit / standby / resume / interval:*)
  if not standby:
    retry any pending uploads to the media server
    capture_and_save("start_of_interval")
  sleep (interval − 2 seconds, interruptible)
  if not standby:
    capture_and_save("end_of_interval")
  sleep (2 seconds, interruptible)
```

### Privacy — face detection

Every captured frame and every dashboard snapshot is passed through a face detector before being saved or transmitted. This ensures no images containing people are stored or sent.

**Retry logic:**
1. Grab a fresh frame from the camera.
2. Run face detection (OpenCV DNN — ResNet-10 SSD, confidence threshold 0.5).
3. If a face is detected: log a `WARN`, wait 5 seconds, try again.
4. After 3 failed retries the 4th attempt is taken regardless and saved, but logged as `FORCED CAPTURE` for review.
5. If no face is detected at any attempt: proceed normally (not logged).

If the face detection model fails to download or load on startup, face detection is disabled for that session (fail-open). A `WARN` is written to `logs/unexpected_events_log.txt` and captures continue uninterrupted.

The model files are stored in `models/` and downloaded automatically on first run:
- `models/deploy.prototxt`
- `models/res10_300x300_ssd_iter_140000_fp16.caffemodel`

### Render polling

A background thread polls the Render dashboard every `POLL_INTERVAL` seconds. On startup it registers the unit. Each poll reports current config, standby state, system health, and network info, and picks up any queued commands:

| Command | Effect |
|---------|--------|
| `request_snapshot` | Captures a full-frame JPEG (no crop, with face detection), sends to dashboard |
| `set_crop` | Updates crop region, saves to `captures/crop.json` |
| `clear_crop` | Removes crop region |
| `set_interval` | Changes capture interval |
| `set_location` | Updates location name, saves to `captures/location.json` |
| `snap` | Triggers an immediate `capture_and_save` |
| `set_standby` | Pauses all captures and uploads — unit stays running |
| `resume` | Resumes normal capture and upload operations |
| `wifi_scan` | Scans for available WiFi networks; POSTs results back to dashboard |
| `wifi_connect` | Connects to the specified WiFi SSID; POSTs result back to dashboard |

### Standby mode

When in standby the unit continues polling the dashboard and processing stdin commands — it simply skips all captures and upload retries. Standby can be toggled from the dashboard or via stdin (`standby` / `resume`).

### System stats

Every poll payload includes a `health` block with live system stats:

| Field | Description |
|-------|-------------|
| `cpu_percent` | CPU utilisation % |
| `memory_percent` | RAM utilisation % |
| `disk_percent` | Disk utilisation % for the captures drive |
| `temperature_celsius` | CPU temperature (Linux/macOS only; `null` on Windows) |
| `battery_percent` | Battery level (laptops only; `null` on desktops) |
| `on_battery` | `true` if running on battery; `null` if no battery |

### Network info

Every poll payload also includes a `network` block:

| Field | Description |
|-------|-------------|
| `ssid` | Active WiFi SSID, or `null` if not connected to WiFi |
| `ip_addresses` | Dict of `{interface: ip}` for all non-loopback IPv4 addresses |

This is how the dashboard always knows which network the unit is on and what IP to SSH into.

### WiFi management

WiFi operations are handled via `nmcli` (NetworkManager CLI). Two commands can be sent from the dashboard:

- **`wifi_scan`**: triggers a rescan (takes 10–30 seconds), then POSTs the results to `/api/units/<id>/wifi_scan` on the dashboard. Results include SSID, signal strength, and whether the network is secured.
- **`wifi_connect`**: attempts to connect to the specified SSID with the given password, then POSTs the success/failure result to `/api/units/<id>/wifi_connect_result`. Both operations run in background threads so they don't block the poll loop.

### Local storage

Every capture is saved to `captures/` before upload is attempted. `captures/uploaded.log` tracks successfully uploaded filenames. Files are never deleted on upload — they are only evicted when the 10 GB cap is hit (oldest first).

### Crop region

- Saved to `captures/crop.json`, loaded on startup.
- Applied to all production captures (`capture_and_save`), including the face-detection retry loop.
- **Not** applied to dashboard snapshots (`take_snapshot`) — the full frame is always sent so you can see the entire scene when drawing a new crop.

### Location name

- Overrides the `LOCATION_NAME` constant in `config.py`.
- Saved to `captures/location.json`, loaded on startup.
- Can be updated from the dashboard or by editing the file directly.

---

## Logging

All log files are written to `logs/` (created automatically). See [LOGS.md](LOGS.md) for full details.

| File | Purpose |
|------|---------|
| `logs/camunit_capture_log.txt` | Face detection discards, forced captures, compression errors, local saves |
| `logs/payload_transmission_log.txt` | Upload attempts, successes, failures, retries, WiFi scan/connect results |
| `logs/crashes_log.txt` | Unhandled exceptions with full tracebacks |
| `logs/unexpected_events_log.txt` | Unknown dashboard commands, model load failures |

All entries are also printed to stdout (visible in `journalctl` when running as a service).

---

## Stdin commands

While the program is running, type a command and press Enter:

| Command | Action |
|---------|--------|
| `snap` | Capture and upload immediately |
| `quit` | Shut down cleanly |
| `standby` | Pause all captures and uploads |
| `resume` | Resume normal operation |
| `interval:30s` | Switch to 30-second interval |
| `interval:1min` | Switch to 1-minute interval |
| `interval:2min` | Switch to 2-minute interval |

---

## Configuration

All constants are in `config.py`:

| Constant | Default | Purpose |
|----------|---------|---------|
| `UNIT_ID` | `"cam-unit-01"` | Unique identifier for this unit |
| `LOCATION_NAME` | `"Front Door Entrance"` | Label embedded in every uploaded payload |
| `RENDER_URL` | `"https://tod-central-dashboard.onrender.com"` | Render dashboard base URL |
| `POLL_INTERVAL` | `5` | Seconds between Render polls |
| `MAX_IMAGE_BYTES` | `1 MB` | Max compressed size per image |
| `MAX_STORAGE_BYTES` | `10 GB` | Total local storage cap |
| `UPLOAD_URL` | `"https://tod.eswarsethu.dev/api/upload"` | Media server upload endpoint |
| `DETECTIONS_URL` | `"https://tod.eswarsethu.dev/api/detections"` | YOLO detections endpoint (stub) |
| `LOGS_DIR` | `Path("logs")` | Directory for all log files |
| `MODELS_DIR` | `Path("models")` | Directory for face detection model files |

---

## Functions reference

### `capture_and_save(label)`
Grabs a fresh frame from the camera manager, applies the active crop region, runs face detection (retrying up to 3 times with 5-second gaps if a face is found), compresses to JPEG (≤ 1 MB), saves locally, and uploads to the media server. Called twice per interval cycle (skipped in standby) and on `snap` commands.

### `take_snapshot()`
Grabs a fresh full frame — no crop applied — runs face detection with the same 3-retry logic, and returns a base64-encoded JPEG at reduced resolution (max 1280 px wide, quality 70). Used exclusively for dashboard snapshot requests.

### `retry_pending_uploads()`
Scans `captures/` for JSON files not in `uploaded.log`. For each, loads the payload and calls `upload_payload`. On success, records the filename in `uploaded.log` (local file is kept). Called at the top of every main loop cycle when not in standby.

### `compress_and_encode_image(frame, max_bytes)`
Encodes a frame as JPEG starting at quality 90, stepping down by 10 until the size fits within `max_bytes`. Returns a base64-encoded UTF-8 string, or `None` if it cannot be brought under the limit.

### `get_health_stats()`
Returns a dict of current system stats (CPU, memory, disk, temperature, battery) collected via `psutil`. Fields are `None` when the underlying sensor is unavailable on the host platform. Called on every poll.

### `get_network_info()`
Returns `{"ssid": str|None, "ip_addresses": {interface: ip}}` using `nmcli` and `psutil`. Called on every poll. Fails gracefully — returns partial data if any step errors.

### `scan_networks()`
Calls `nmcli dev wifi list --rescan yes` and returns a list of `{"ssid", "signal", "secured"}` dicts sorted by signal strength (strongest first). Blocks for up to 40 seconds — always called from a background thread.

### `connect_to_network(ssid, password)`
Calls `nmcli dev wifi connect <ssid> password <password>`. Returns `(success: bool, message: str)`. Blocks for up to 40 seconds — always called from a background thread.

### `load_model()`
Downloads the face detection model files to `models/` if missing, then loads them with `cv2.dnn.readNetFromCaffe`. On failure, logs to `unexpected_events_log.txt` and sets the model to `None` (fail-open). Called once at startup.

### `has_faces(frame)`
Returns `True` if the face detector finds at least one detection above the 0.5 confidence threshold. Returns `False` if the model failed to load. Called for every frame before it is saved or transmitted.

### `interruptible_sleep(seconds, cmd_queue, stop_event, unit_state)`
Sleeps in 0.5-second ticks, processing commands as they arrive. Handles `snap`, `quit`, `standby`, `resume`, and `interval:*` mid-sleep. Returns `"quit"` if an exit command is received, otherwise `None`.

### `run_yolo_detection(frame)` *(stub)*
Returns `[]`. Intended to run YOLO inference on the frame and return a list of `{"label", "confidence", "bbox"}` dicts.

### `upload_detections(detections, timestamp, location, label)` *(stub)*
Does nothing (`pass`). Intended to POST detection results to `DETECTIONS_URL`.

---

## Server API

See [ENDPOINTS.md](ENDPOINTS.md) for request and response schemas for the media server endpoints.
