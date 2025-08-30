FROM python:3.11-slim

# Install system dependencies for healthcare data processing
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    postgresql-client \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY update-scripts/ ./update-scripts/
COPY config/ ./config/

# Create data and logs directories and set script permissions
RUN mkdir -p /app/data /app/logs && \
    chmod 755 /app/data /app/logs && \
    chmod +x /app/update-scripts/*.sh

# Set Python path
ENV PYTHONPATH=/app/src

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "/app/src/main.py"]
