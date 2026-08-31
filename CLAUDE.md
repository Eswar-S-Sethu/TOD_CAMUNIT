# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the camera unit

```bash
# Activate the virtual environment (Python 3.12)
.venv\Scripts\activate

# --interval is required
python main.py --interval 30s
python main.py --interval 1min
python main.py --interval 2min
```

While running, type commands and press Enter:
- `snap` — capture immediately
- `quit` — shut down cleanly
- `interval:30s` / `interval:1min` / `interval:2min` — change interval at runtime

## Dependencies

No `requirements.txt`. Install manually:

```bash
pip install opencv-python requests psutil
```

- `opencv-python` (`cv2`) — camera capture and JPEG encoding
- `requests` — HTTP uploads and Render polling
- `psutil` — system stats (CPU, memory, disk, temperature, battery) reported to dashboard on every poll

There is no test suite. Manual testing requires a connected webcam and the media server reachable at `https://tod.eswarsethu.dev`. The Render client connects to `https://tod-central-dashboard.onrender.com`.

## Architecture

`main.py` is the entry point. All logic lives in the other modules.

| Module | Responsibility |
|--------|---------------|
| `config.py` | All constants — URLs, IDs, paths, size limits, poll interval |
| `health.py` | `get_health_stats()` — CPU %, memory %, disk %, temperature, battery via psutil |
| `network.py` | `upload_payload()` — POST to local media server |
| `detection.py` | `run_yolo_detection()`, `upload_detections()` — both stubs |
| `storage.py` | Local 10 GB rolling queue — save, retry, upload tracking |
| `crop.py` | Crop region load/save/apply — persisted to `captures/crop.json` |
| `location.py` | Location name load/save — persisted to `captures/location.json` (overrides `config.py` default) |
| `camera_manager.py` | `CameraManager` singleton — continuous background frame read loop |
| `camera.py` | `capture_and_save()`, `take_snapshot()`, `compress_and_encode_image()` |
| `render_client.py` | Polls Render dashboard every `POLL_INTERVAL` s, handles commands |
| `commands.py` | `input_listener()` (stdin daemon), `interruptible_sleep()` |
| `main.py` | `parse_args()`, shared `unit_state` dict, main loop |

**Dependency order:** `config` ← `network` / `crop` ← `storage` ← `camera_manager` ← `camera` ← `render_client` / `commands` ← `main`

**Shared mutable state:** `unit_state = {"interval": str, "interval_secs": int, "location": str}` is a dict created in `main()` and passed into `render_client` and `interruptible_sleep`. Both can update it so interval/location changes take effect immediately.

**Main loop cycle:**
1. Drain stdin commands (snap / quit / interval:*)
2. `retry_pending_uploads()` — retries any locally stored captures not yet uploaded
3. `capture_and_save("start_of_interval")`
4. `interruptible_sleep(interval_secs - 2, ...)` — handles commands mid-sleep
5. `capture_and_save("end_of_interval")`
6. `interruptible_sleep(2, ...)`

**Render polling (background thread):**
- Registers unit on startup: `POST /api/units/register`
- Every `POLL_INTERVAL` seconds: `POST /api/units/<id>/poll` — returns queued commands
- Commands: `request_snapshot`, `set_crop`, `clear_crop`, `set_interval`, `set_location`, `snap`, `stop`
- `request_snapshot` → calls `take_snapshot()` → `POST /api/units/<id>/snapshot`

**Snapshot vs production capture:**
- `take_snapshot()` — full frame, no crop, lower resolution/quality, for dashboard display only
- `capture_and_save()` — applies crop region, full quality, saved locally + uploaded to media server

**Local storage:** Every capture saved to `captures/` before upload is attempted. `captures/uploaded.log` tracks uploaded filenames. Files evicted only when 10 GB cap is hit. `captures/crop.json` persists the crop region; `captures/location.json` persists the location name — both persist across restarts.

**Dashboard:** Separate git repo, deployed to `https://tod-central-dashboard.onrender.com`.

## Stubs to implement

Both stubs live in `detection.py`:
- **`run_yolo_detection(frame)`** — returns `[]`. Should run YOLO inference and return `[{"label", "confidence", "bbox"}, ...]`.
- **`upload_detections(...)`** — `pass`. Should POST to `DETECTIONS_URL`.

## Configuration

Edit constants in `config.py`:

| Constant | Purpose |
|----------|---------|
| `UNIT_ID` | Unique identifier for this camera unit |
| `LOCATION_NAME` | Human-readable label embedded in every payload |
| `RENDER_URL` | Base URL of the deployed Render dashboard |
| `POLL_INTERVAL` | Seconds between Render polls (default 5) |
| `UPLOAD_URL` | Local media server image upload endpoint |
| `DETECTIONS_URL` | YOLO detections endpoint (stub, unused) |
| `MAX_IMAGE_BYTES` | Max compressed image size (default 1 MB) |
| `MAX_STORAGE_BYTES` | Local storage cap (default 10 GB) |

## Reference docs

- `README.md` — setup, usage, commands, and functions reference
- `ENDPOINTS.md` — request/response schemas for the local media server API
