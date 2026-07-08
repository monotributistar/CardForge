# CardForge Core API — compile service (FastAPI + manifold3d).
# Build:  docker build -t cardforge-core .
# Run:    docker run -p 9000:9000 cardforge-core
FROM python:3.11-slim

# Outline fonts for text features (the kernel filters to outline-capable
# faces; these three families give sans/serif/mono coverage).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-dejavu-core fonts-liberation fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 9000
CMD ["uvicorn", "cardforge.api.server:app", "--host", "0.0.0.0", "--port", "9000"]
