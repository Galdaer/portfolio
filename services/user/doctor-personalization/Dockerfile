FROM python:3.11-slim

# Install system dependencies for AI/ML and personalization
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directories and set permissions
RUN mkdir -p /app/logs /app/models/adapters && \
    chmod 755 /app/logs /app/models

# Set Python path
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Expose port
EXPOSE 8007

# Run the application
CMD ["python", "/app/src/main.py"]