FROM python:3.12-slim

WORKDIR /app

# Runtime dependency required by OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY *.py .

RUN pip install --no-cache-dir opencv-python-headless requests

# captures/ stores all local images; crop.json persists the active crop region
VOLUME /app/captures

ENTRYPOINT ["python", "main.py"]
# Override --interval at runtime: docker run ... tod-camunit --interval 30s
CMD ["--interval", "1min"]
