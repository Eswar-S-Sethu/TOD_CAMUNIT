import base64
import time
from datetime import datetime

import cv2

from camera_manager import camera as cam
from config import MAX_IMAGE_BYTES
from crop import apply_crop
from detection import run_yolo_detection, upload_detections
from face_detection import has_faces
from location import get_location
from logger import log_capture
from network import upload_payload
from storage import mark_as_uploaded, save_locally

_SNAPSHOT_MAX_WIDTH = 1280
_SNAPSHOT_QUALITY   = 70
_FACE_MAX_RETRIES   = 3
_FACE_RETRY_DELAY   = 5  # seconds between retries


def _get_face_checked_frame(get_frame_fn, context):
    """
    Calls get_frame_fn() to obtain a fresh frame and checks it for faces.
    Retries up to _FACE_MAX_RETRIES times (with a delay) if faces are found.
    On the 4th attempt the frame is returned regardless and a forced-capture
    warning is written to the capture log.

    get_frame_fn — callable returning a fresh frame (or None if camera unavailable)
    context      — short label used in log messages

    Returns the frame, or None if the camera produced no frame on the last attempt.
    """
    for attempt in range(1, _FACE_MAX_RETRIES + 2):  # attempts 1..4
        frame = get_frame_fn()
        if frame is None:
            return None

        if not has_faces(frame):
            return frame

        if attempt <= _FACE_MAX_RETRIES:
            log_capture(
                "WARN",
                f"[{context}] Face detected — discarding frame "
                f"(attempt {attempt}/{_FACE_MAX_RETRIES}), retrying in {_FACE_RETRY_DELAY}s",
            )
            time.sleep(_FACE_RETRY_DELAY)
        else:
            log_capture(
                "WARN",
                f"[{context}] FORCED CAPTURE — face still detected after "
                f"{_FACE_MAX_RETRIES} retries. Frame taken and flagged.",
            )

    return frame  # reached only on 4th attempt (forced)


def compress_and_encode_image(frame, max_bytes=MAX_IMAGE_BYTES):
    """JPEG-encodes frame, stepping quality down until it fits within max_bytes."""
    for quality in range(90, 10, -10):
        success, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )
        if success and len(buffer) <= max_bytes:
            return base64.b64encode(buffer).decode("utf-8")
    return None


def take_snapshot():
    """
    Captures the full frame with no crop applied, resized for dashboard preview.
    Checks for faces and retries up to _FACE_MAX_RETRIES times before a forced capture.
    Used only for dashboard display — not saved locally.
    Returns (base64_str, width, height) or (None, None, None) on failure.
    """
    frame = _get_face_checked_frame(cam.get_frame, "take_snapshot")
    if frame is None:
        log_capture("ERROR", "[take_snapshot] No frame available from camera.")
        return None, None, None

    h, w = frame.shape[:2]
    if w > _SNAPSHOT_MAX_WIDTH:
        scale = _SNAPSHOT_MAX_WIDTH / w
        frame = cv2.resize(frame, (_SNAPSHOT_MAX_WIDTH, int(h * scale)))
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), _SNAPSHOT_QUALITY])
    return base64.b64encode(buf).decode("utf-8"), frame.shape[1], frame.shape[0]


def capture_and_save(label):
    """
    Grabs the latest frame, applies the active crop region, checks for faces
    (retrying up to _FACE_MAX_RETRIES times), saves a local copy, then attempts upload.
    """
    def _get_cropped_frame():
        f = cam.get_frame()
        return apply_crop(f) if f is not None else None

    frame = _get_face_checked_frame(_get_cropped_frame, label)
    if frame is None:
        log_capture("ERROR", f"[{label}] No frame available from camera.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detections = run_yolo_detection(frame)
    base64_image = compress_and_encode_image(frame)

    if not base64_image:
        log_capture("ERROR", f"[{label}] Image compression failed.")
        return

    location = get_location()
    payload = {
        "timestamp": timestamp,
        "location": location,
        "timing_label": label,
        "image_format": "jpg",
        "image_base64": base64_image,
    }

    filepath = save_locally(payload, label)

    if upload_payload(payload):
        print(f"Uploaded: {label} @ {timestamp}")
        mark_as_uploaded(filepath.name)
    else:
        print(f"Upload failed — saved locally: {filepath.name}")

    upload_detections(detections, timestamp, location, label)
