# Media Server Endpoints Reference

Base URL: `https://tod.eswarsethu.dev`

---

## POST `/api/upload`

Receives a single camera capture — the image, timestamp, and location metadata.

### Request

| Field | Value |
|---|---|
| Method | `POST` |
| Content-Type | `application/json` |
| Timeout | 10 seconds |

### Request Body

```json
{
    "timestamp":    "2024-01-15 09:30:00",
    "location":     "Front Door Entrance",
    "timing_label": "start_of_interval",
    "image_format": "jpg",
    "image_base64": "<base64-encoded JPEG string>"
}
```

### Field Descriptions

| Field | Type | Description |
|---|---|---|
| `timestamp` | `string` | Local capture time, format `YYYY-MM-DD HH:MM:SS` |
| `location` | `string` | Label identifying the camera unit (from `config.py` or `captures/location.json`) |
| `timing_label` | `string` | `"start_of_interval"`, `"end_of_interval"`, or `"on_demand"` |
| `image_format` | `string` | Always `"jpg"` |
| `image_base64` | `string` | Base64-encoded JPEG. Maximum decoded size: 1 MB |

### Response

| Status | Meaning |
|---|---|
| `200` | Payload accepted. The camera unit marks the capture as uploaded in `uploaded.log`. |
| Any other / timeout | Treated as failure. The capture stays in `captures/` and is retried at the start of the next loop cycle. |

The response body is not read by the camera unit — only the status code matters.

---

## POST `/api/detections` *(STUB — not yet implemented)*

Will receive YOLO detection results separately from the image, once the model is trained and integrated. This endpoint and its corresponding client function are stubs; no data is sent yet.

### Request

| Field | Value |
|---|---|
| Method | `POST` |
| Content-Type | `application/json` |
| Timeout | TBD |

### Request Body (planned)

```json
{
    "timestamp":    "2024-01-15 09:30:00",
    "location":     "Front Door Entrance",
    "timing_label": "start_of_interval",
    "detections": [
        {
            "label":      "person",
            "confidence": 0.94,
            "bbox":       [120, 45, 380, 510]
        }
    ]
}
```

### Field Descriptions

| Field | Type | Description |
|---|---|---|
| `timestamp` | `string` | Local capture time, format `YYYY-MM-DD HH:MM:SS` |
| `location` | `string` | Label identifying the camera unit |
| `timing_label` | `string` | `"start_of_interval"`, `"end_of_interval"`, or `"on_demand"` |
| `detections` | `array` | List of YOLO detection objects |

### Detection Object

| Field | Type | Description |
|---|---|---|
| `label` | `string` | Detected class name (e.g. `"person"`, `"car"`) |
| `confidence` | `float` | Confidence score, range `0.0` – `1.0` |
| `bbox` | `array[int]` | Bounding box as `[x1, y1, x2, y2]` in pixel coordinates relative to the original frame |

### Response

TBD — to be defined when the endpoint is implemented.

---

## Retry Behaviour

When a POST to `/api/upload` fails (non-200 or timeout), the capture payload has already been saved as a local JSON file (`captures/capture_YYYYMMDD_HHMMSS_<label>.json`). At the start of the next loop cycle — provided the unit is not in standby — all pending local files are replayed against `/api/upload` in chronological order. Successfully uploaded filenames are recorded in `captures/uploaded.log`; the JSON files themselves are kept and only evicted when the 10 GB local storage cap is reached.

Retry behaviour for `/api/detections` is TBD.
