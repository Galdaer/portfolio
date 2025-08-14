# SciSpacy Healthcare NLP Service
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application files
COPY app/ /app/

# Install Python dependencies in correct order to avoid binary incompatibilities
RUN uv pip install --system --no-cache "numpy>=1.21.0,<1.27.0" && \
    uv pip install --system --no-cache \
    scispacy \
    spacy \
    flask \
    requests \
    pyyaml

# Install SciSpacy model (cached in Docker layer)
RUN uv pip install --system \
    https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz

# Test model installation during build
RUN python -c "import spacy; nlp = spacy.load('en_ner_bionlp13cg_md'); print('Model loaded successfully')"

# Set environment variables
ENV SPACY_MODEL=en_ner_bionlp13cg_md
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=8001
ENV PYTHONUNBUFFERED=1
ENV METADATA_PATH=/app/metadata.sample.yml
ENV DEFAULT_ENRICH=false
ENV SCISPACY_CACHE=true
ENV SCISPACY_CACHE_SIZE=256
ENV SCISPACY_CACHE_TTL=300

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fs http://localhost:8001/health || exit 1

# Start the server directly (no need for entrypoint.sh now)
CMD ["python", "/app/scispacy_server.py"]
