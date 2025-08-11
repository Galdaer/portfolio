FROM python:3.12-slim

# Healthcare API metadata with security documentation
LABEL maintainer="Intelluxe AI Healthcare Team"
LABEL description="HIPAA-compliant Healthcare API with administrative support agents"
LABEL version="1.0.0"
LABEL security="hardened-healthcare"

# Create intelluxe group and user
RUN groupadd -g 1001 intelluxe && \
    useradd -u 1000 -g 1001 -m -s /bin/bash api

# Security hardening - update packages and install required tools including Docker
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    ca-certificates \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Add api user to docker group for container communication
RUN usermod -a -G docker api

WORKDIR /app

# Copy healthcare-api specific requirements
# Copy requirements (specific to healthcare-api)
COPY --chown=api:intelluxe requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy healthcare-api source code
COPY --chown=api:intelluxe . ./

# Create logs directory
RUN mkdir -p /app/logs && chown -R api:intelluxe /app/logs

# Ensure proper permissions
RUN chown -R api:intelluxe /app

USER api

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
