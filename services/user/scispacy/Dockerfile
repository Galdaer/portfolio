# SciSpacy Healthcare NLP Service with GPU support
# Using NVIDIA CUDA runtime image based on Ubuntu 24.04 LTS
FROM nvidia/cuda:12.6.2-runtime-ubuntu24.04

# Install Python and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    curl \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3 /usr/bin/python

# Use system pip with break-system-packages for Ubuntu 24.04
# (upgrading pip causes issues with debian-managed pip)

# Set working directory
WORKDIR /app

# Copy application files
COPY app/ /app/

# Install PyTorch nightly with CUDA 12.9 support for RTX 5060 Ti (sm_120)
RUN pip3 install --break-system-packages --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu129

# Install Python dependencies in correct order to avoid binary incompatibilities
# Skip CuPy for now due to sm_120 compatibility issues
RUN pip3 install --break-system-packages "numpy>=1.21.0,<1.27.0" && \
    pip3 install --break-system-packages \
    scispacy \
    spacy[transformers] \
    flask \
    requests \
    pyyaml

# Install SciSpacy model (cached in Docker layer)
RUN pip3 install --break-system-packages \
    https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bionlp13cg_md-0.5.4.tar.gz

# Test model and CUDA installation during build
RUN python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device count: {torch.cuda.device_count()}')" && \
    python -c "import spacy; nlp = spacy.load('en_ner_bionlp13cg_md'); print('Model loaded successfully')"

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
