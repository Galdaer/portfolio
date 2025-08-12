FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (curl for diagnostics, docker for container communication)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and add to docker group
RUN groupadd -g 1001 intelluxe && \
    useradd -u 1000 -g 1001 -m -s /bin/bash pipeline

# Add pipeline user to docker group for container communication
RUN groupmod -g 984 docker && usermod -a -G docker pipeline

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy minimal pipeline code
COPY pipelines/ ./pipelines/
COPY start_pipeline.sh .

RUN chown -R pipeline:intelluxe /app && chmod +x start_pipeline.sh

USER pipeline

EXPOSE 9099

HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fs http://localhost:9099/health || exit 1

CMD ["./start_pipeline.sh"]
