# Log Files Reference

All log files are written to the `logs/` directory at the project root.
The directory is created automatically on startup if it does not exist.

Each entry follows this format:

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] message
```

Log levels used: `INFO`, `WARN`, `ERROR`, `CRASH`

All entries are also printed to stdout so they appear in the terminal and in
any service manager output (e.g. `journalctl` when running via systemd).

---

## `logs/camunit_capture_log.txt`

**Purpose:** Records notable capture events — primarily privacy-related
discards and errors. Clean captures with no issues are not logged here to
keep the file focused on events that need attention.

**Events logged:**

| Event | Level | Description |
|-------|-------|-------------|
| Face detected — discarding frame | `WARN` | A face was found in the frame. The frame is discarded and a fresh one will be taken after 5 seconds. Includes the attempt number out of the maximum 3 retries. |
| FORCED CAPTURE — face still detected | `WARN` | All 3 retries were exhausted and a face is still present. The 4th frame is taken and saved regardless, but this entry flags it for review. |
| No frame available from camera | `ERROR` | The camera produced no frame. Capture skipped for this cycle. |
| Image compression failed | `ERROR` | The frame could not be compressed within the 1 MB limit across all quality steps. Capture skipped. |
| Saved locally: `<filename>` | `INFO` | A capture payload was written to the local rolling store in `captures/`. |

---

## `logs/payload_transmission_log.txt`

**Purpose:** Records every upload attempt to the media server and the
Render dashboard, both successes and failures. Use this to diagnose
connectivity issues and verify data is reaching its destinations.

**Events logged:**

| Event | Level | Description |
|-------|-------|-------------|
| Uploaded payload `[label]` @ `<timestamp>` | `INFO` | A capture payload was successfully accepted by the media server (`HTTP 200`). |
| Upload rejected (HTTP `<code>`) | `WARN` | The media server returned a non-200 status. The payload remains in the local store for retry. |
| Upload failed `[label]` @ `<timestamp>` | `WARN` | A network or timeout error prevented the upload. The payload remains in the local store for retry. |
| Retry upload succeeded: `<filename>` | `INFO` | A previously failed payload was successfully uploaded on a retry cycle. |
| Retry upload failed: `<filename>` | `WARN` | A retry upload attempt also failed. The file will be retried on the next cycle. |
| Retry error for `<filename>` | `WARN` | An unexpected error occurred while reading or uploading a retry payload. |
| Snapshot sent to Render dashboard | `INFO` | A dashboard preview snapshot was successfully posted to the Render endpoint. |
| Snapshot requested but no frame available | `WARN` | A snapshot was requested from the dashboard but the camera returned nothing (or all face-detection retries were exhausted). |
| Could not register with Render dashboard | `WARN` | The unit registration POST on startup failed. The unit will still operate locally. |
| Poll to Render dashboard failed | `WARN` | A polling request to the Render dashboard failed. Commands may be delayed until connectivity is restored. |

---

## `logs/crashes_log.txt`

**Purpose:** Records unhandled exceptions from the main loop with their
full Python traceback. If the program exits unexpectedly, this file is
the first place to check.

**Events logged:**

| Event | Level | Description |
|-------|-------|-------------|
| Unhandled exception in main loop | `CRASH` | Full `traceback.format_exc()` output including exception type, message, and stack trace. |

After a crash entry is written the exception is re-raised, so the process
exits with a non-zero status code (visible in systemd or process monitors).

---

## `logs/unexpected_events_log.txt`

**Purpose:** Records anomalous events that do not fit the other categories —
unknown dashboard commands, model loading failures, and other conditions
that should not occur during normal operation.

**Events logged:**

| Event | Level | Description |
|-------|-------|-------------|
| Unknown command type from dashboard | `WARN` | The dashboard sent a command whose `type` field is not handled by the unit. May indicate a dashboard/unit version mismatch. |
| Failed to download model file | `ERROR` | The face detection model could not be downloaded on first run. Face detection will be disabled for this session. |
| Face detection model failed to load | `ERROR` | The model files exist but OpenCV could not load them (corrupt file, version mismatch, etc.). Face detection will be disabled. |

If face detection is disabled due to a model error, the unit will continue
capturing normally but **will not perform face checks**. This is a
fail-open design to avoid blocking all captures due to a model issue.
Review this log and re-download the model files if this occurs.
