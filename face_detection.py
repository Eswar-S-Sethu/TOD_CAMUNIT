"""
OpenCV DNN-based face detector for privacy protection.

Uses the SSD ResNet-10 Caffe model (fp16). Model files are auto-downloaded
to the models/ directory on first run if they are not already present.

Public API:
  load_model()        — call once at startup
  has_faces(frame)    — returns True if ≥1 face is detected above threshold
"""
import urllib.request
from pathlib import Path

import cv2

from config import MODELS_DIR
from logger import log_unexpected

_PROTOTXT_URL   = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
_CAFFEMODEL_URL = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20180205_fp16/res10_300x300_ssd_iter_140000_fp16.caffemodel"

_PROTOTXT_PATH   = MODELS_DIR / "deploy.prototxt"
_CAFFEMODEL_PATH = MODELS_DIR / "res10_300x300_ssd_iter_140000_fp16.caffemodel"

_CONFIDENCE_THRESHOLD = 0.5

_net = None  # loaded DNN network; None until load_model() succeeds


def _download_if_missing():
    """Downloads model files if they are not already present in models/."""
    MODELS_DIR.mkdir(exist_ok=True)
    files = [
        (_PROTOTXT_PATH,   _PROTOTXT_URL,   "deploy.prototxt"),
        (_CAFFEMODEL_PATH, _CAFFEMODEL_URL, "res10_300x300_ssd_iter_140000_fp16.caffemodel"),
    ]
    for path, url, name in files:
        if not path.exists():
            print(f"Downloading face detection model: {name} ...")
            try:
                urllib.request.urlretrieve(url, path)
                print(f"Downloaded: {name}")
            except Exception as e:
                log_unexpected("ERROR", f"Failed to download {name} from {url}: {e}")
                raise RuntimeError(f"Could not download model file '{name}': {e}") from e


def load_model():
    """
    Loads the OpenCV DNN face detection model.
    Downloads model files first if they are missing.
    Call this once at startup before any calls to has_faces().
    """
    global _net
    try:
        _download_if_missing()
        _net = cv2.dnn.readNetFromCaffe(str(_PROTOTXT_PATH), str(_CAFFEMODEL_PATH))
        print("Face detection model loaded.")
    except Exception as e:
        log_unexpected("ERROR", f"Face detection model failed to load: {e}")
        _net = None


def has_faces(frame) -> bool:
    """
    Returns True if the frame contains at least one detected face
    above the confidence threshold. Returns False if the model is
    not loaded (fails open — does NOT block captures if model unavailable).
    """
    if _net is None:
        return False

    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0),
    )
    _net.setInput(blob)
    detections = _net.forward()

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence >= _CONFIDENCE_THRESHOLD:
            return True
    return False
