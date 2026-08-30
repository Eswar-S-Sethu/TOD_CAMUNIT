from config import DETECTIONS_URL  # noqa: F401 — will be used when stubs are implemented


def run_yolo_detection(frame):
    """
    STUB — replace with real YOLO inference once the model is trained.

    Expected return format (list of dicts, one per detected object):
    [
        {
            "label":      str,    # class name, e.g. "person", "car"
            "confidence": float,  # 0.0 – 1.0
            "bbox":       [x1, y1, x2, y2]  # pixel coords in the original frame
        },
        ...
    ]
    """
    # TODO: load model weights and run inference on `frame`
    return []


def upload_detections(detections, timestamp, location, label):
    """
    STUB — sends YOLO detections to the server separately from the image.
    Will be implemented once the YOLO model is ready.
    """
    # TODO: POST to DETECTIONS_URL once model and endpoint are ready
    pass
