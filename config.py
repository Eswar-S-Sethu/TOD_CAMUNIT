from pathlib import Path

# Camera / location
LOCATION_NAME = "Front Door Entrance"
UNIT_ID       = "cam-unit-01"          # Unique ID for this unit — change per device

# Image size cap (bytes, after JPEG compression)
MAX_IMAGE_BYTES = 1 * 1024 * 1024            # 1 MB

# Local rolling storage cap
MAX_STORAGE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
STORAGE_DIR = Path("captures")
UPLOADED_LOG = STORAGE_DIR / "uploaded.log"

# Render dashboard
RENDER_URL     = "https://tod-central-dashboard.onrender.com"
POLL_INTERVAL  = 5                                       # seconds between Render polls

# Media server (stores production captures)
UPLOAD_URL     = "https://tod.eswarsethu.dev/api/upload"
DETECTIONS_URL = "https://tod.eswarsethu.dev/api/detections"  # STUB — not yet used
