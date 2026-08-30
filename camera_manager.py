import threading
import time

import cv2


class CameraManager:
    """
    Reads frames from the camera continuously in a background thread so that
    both the live stream server and scheduled captures share one device handle.
    """

    def __init__(self):
        self._frame = None
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def start(self):
        """Starts the background read loop."""
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()

    def _read_loop(self):
        cam = None
        while not self._stop.is_set():
            if cam is None or not cam.isOpened():
                cam = cv2.VideoCapture(0)
                if not cam.isOpened():
                    print("Warning: Camera not available — retrying in 5 s")
                    time.sleep(5)
                    continue
            ret, frame = cam.read()
            if ret:
                with self._lock:
                    self._frame = frame
            else:
                cam.release()
                cam = None
        if cam and cam.isOpened():
            cam.release()

    def get_frame(self):
        """Returns a copy of the latest frame, or None if not yet available."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self):
        """Signals the read loop to exit."""
        self._stop.set()


# Module-level singleton shared by camera.py, stream_server.py, and main.py
camera = CameraManager()
