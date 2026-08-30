# TOD Camera Unit

A modular camera unit that captures images at a configurable interval and uploads them to a local media server. All captures are stored locally as a rolling 10 GB archive. A separate web dashboard hosted on Render lets you monitor units, request snapshots, set crop regions, and change settings remotely.

---

## Camera unit

### Requirements

- Python 3.12
- A connected webcam
- A running local media server at `http://localhost:5000` (see [ENDPOINTS.md](ENDPOINTS.md))
- A deployed Render dashboard (see below) — or `http://localhost:5000` for local testing

### Setup

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
pip install opencv-python requests
```

**3. Configure `config.py`**

| Constant | Default | What to set |
|----------|---------|-------------|
| `UNIT_ID` | `"cam-unit-01"` | Unique ID for this camera unit |
| `LOCATION_NAME` | `"Front Door Entrance"` | Human-readable label |
| `RENDER_URL` | `"https://tod-central-dashboard.onrender.com"` | URL of the Render dashboard |
| `UPLOAD_URL` | `"http://localhost:5000/api/upload"` | Local media server upload endpoint |
| `POLL_INTERVAL` | `5` | Seconds between dashboard polls |

### Running

`--interval` is required. Choose from `30s`, `1min`, or `2min`.

```bash
python main.py --interval 30s
python main.py --interval 1min
python main.py --interval 2min
```

**Example output:**

```
Camera unit starting — interval: 1min | location: Front Door Entrance
Commands: 'snap' | 'quit' | 'interval:30s' | 'interval:1min' | 'interval:2min'
```

### Docker

**Build the image:**

```bash
docker build -t tod-camunit .
```

**Run interactively** (required for stdin commands):

```bash
docker run -it \
  --device /dev/video0 \
  -v $(pwd)/captures:/app/captures \
  tod-camunit --interval 1min
```

**Run detached** (dashboard-controlled only):

```bash
docker run -d \
  --device /dev/video0 \
  -v $(pwd)/captures:/app/captures \
  tod-camunit --interval 1min
```

- `--device /dev/video0` — pass the webcam into the container. Adjust if your camera is at `/dev/video1`, etc.
- `-v $(pwd)/captures:/app/captures` — mounts local storage so captures and `crop.json` survive restarts.
- The default interval is `1min`. Pass `--interval 30s` or `--interval 2min` to override.

> **Server URL inside a container:** `localhost` inside Docker refers to the container itself. Use `host.docker.internal` (Docker Desktop) or the host's LAN IP in `config.py` when the server runs on the host machine.

---

## Render dashboard

The central dashboard is a separate project deployed to Render at:

**https://tod-central-dashboard.onrender.com**

Update `RENDER_URL` in `config.py` if the dashboard URL ever changes.

---

## How it works

### Capture cycle

Each cycle captures two photos — one at the start and one near the end of the interval — then repeats.

```
loop:
  drain stdin commands (snap / quit / interval:*)
  retry any pending uploads to the local media server
  capture_and_save("start_of_interval")
  sleep (interval − 2 seconds, interruptible)
  capture_and_save("end_of_interval")
  sleep (2 seconds, interruptible)
```

### Render polling

A background thread polls the Render dashboard every `POLL_INTERVAL` seconds. On startup it registers the unit. Each poll delivers the current config and picks up any queued commands:

| Command | Effect |
|---------|--------|
| `request_snapshot` | Captures a full-frame JPEG (no crop), sends to dashboard |
| `set_crop` | Updates crop region, saves to `captures/crop.json` |
| `clear_crop` | Removes crop region |
| `set_interval` | Changes capture interval |
| `snap` | Triggers an immediate `capture_and_save` |
| `stop` | Shuts the unit down cleanly |

### Local storage

Every capture is saved to `captures/` before upload is attempted. `captures/uploaded.log` tracks successfully uploaded filenames. Files are never deleted on upload — only evicted when the 10 GB cap is hit (oldest first).

### Crop region

- Saved to `captures/crop.json`, loaded on startup.
- Applied to all production captures (`capture_and_save`).
- **Not** applied to dashboard snapshots (`take_snapshot`) — the full frame is always sent so you can see the entire scene when drawing a new crop.
- Survives container restarts because `captures/` is a Docker volume mount.

---

## Stdin commands

While the program is running, type a command and press Enter:

| Command | Action |
|---------|--------|
| `snap` | Capture and upload immediately |
| `quit` | Shut down cleanly |
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
| `RENDER_URL` | `"https://your-dashboard.onrender.com"` | Render dashboard base URL |
| `POLL_INTERVAL` | `5` | Seconds between Render polls |
| `MAX_IMAGE_BYTES` | `1 MB` | Max compressed size per image |
| `MAX_STORAGE_BYTES` | `10 GB` | Total local storage cap |
| `UPLOAD_URL` | `http://localhost:5000/api/upload` | Local media server upload endpoint |
| `DETECTIONS_URL` | `http://localhost:5000/api/detections` | YOLO detections endpoint (stub) |

---

## Functions reference

### `capture_and_save(label)`
Grabs the latest frame from the camera manager, applies the active crop region, compresses to JPEG (≤ 1 MB), saves locally, and uploads to the local media server. Called twice per interval cycle and on `snap` commands.

### `take_snapshot()`
Grabs the latest frame — full frame, no crop applied — and returns a base64-encoded JPEG at reduced resolution (max 1280 px wide, quality 70). Used exclusively for dashboard snapshot requests.

### `retry_pending_uploads()`
Scans `captures/` for JSON files not in `uploaded.log`. For each, loads the payload and calls `upload_payload`. On success, records the filename in `uploaded.log` (local file is kept). Called at the top of every main loop cycle.

### `compress_and_encode_image(frame, max_bytes)`
Encodes a frame as JPEG starting at quality 90, stepping down by 10 until the size fits within `max_bytes`. Returns a base64-encoded UTF-8 string, or `None` if it cannot be brought under the limit.

### `interruptible_sleep(seconds, cmd_queue, stop_event, unit_state)`
Sleeps in 0.5-second ticks, processing commands as they arrive. Handles `snap`, `quit`, and `interval:*` mid-sleep. Returns `"quit"` if an exit command is received, otherwise `None`.

### `run_yolo_detection(frame)` *(stub)*
Returns `[]`. Intended to run YOLO inference on the frame and return a list of `{"label", "confidence", "bbox"}` dicts.

### `upload_detections(detections, timestamp, location, label)` *(stub)*
Does nothing (`pass`). Intended to POST detection results to `DETECTIONS_URL`.

---

## Server API

See [ENDPOINTS.md](ENDPOINTS.md) for request and response schemas for the local media server endpoints.
