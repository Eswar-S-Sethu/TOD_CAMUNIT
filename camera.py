import base64
from datetime import datetime

import cv2

from camera_manager import camera as cam
from config import MAX_IMAGE_BYTES
from crop import apply_crop
from location import get_location
from detection import run_yolo_detection, upload_detections
from network import upload_payload
from storage import mark_as_uploaded, save_locally

_SNAPSHOT_MAX_WIDTH = 1280
_SNAPSHOT_QUALITY   = 70


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
    Used only for crop setup on the Render dashboard — not saved locally.
    Returns (base64_str, width, height) or (None, None, None) on failure.
    """
    frame = cam.get_frame()
    if frame is None:
        return None, None, None
    h, w = frame.shape[:2]
    if w > _SNAPSHOT_MAX_WIDTH:
        scale = _SNAPSHOT_MAX_WIDTH / w
        frame = cv2.resize(frame, (_SNAPSHOT_MAX_WIDTH, int(h * scale)))
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), _SNAPSHOT_QUALITY])
    return base64.b64encode(buf).decode("utf-8"), frame.shape[1], frame.shape[0]


def capture_and_save(label):
    """
    Grabs the latest frame, applies the active crop region, saves a local copy,
    then attempts to upload to the media server.
    """
    frame = cam.get_frame()
    if frame is None:
        print(f"Error: No frame available from camera for '{label}'.")
        return

    frame = apply_crop(frame)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detections = run_yolo_detection(frame)
    base64_image = compress_and_encode_image(frame)

    if not base64_image:
        print(f"Image compression failed for '{label}'.")
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
