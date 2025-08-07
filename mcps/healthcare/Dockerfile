# Intelluxe AI Healthcare MCP Server Dockerfile
# Secure, HIPAA-compliant container for healthcare AI MCP server
FROM node:20-slim

# Healthcare AI metadata with security documentation
LABEL maintainer="Intelluxe AI Healthcare Team"
LABEL description="HIPAA-compliant MCP server for healthcare AI workflows"
LABEL version="1.0.1"
LABEL security="hardened-healthcare"
LABEL documentation="Security assessment: Network-isolated deployment mitigates container CVEs"

# Security: Create intelluxe group and add node user to it
RUN groupadd -g 1001 intelluxe && usermod -a -G intelluxe node

# Security hardening - update all packages and install Python
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy authentication proxy requirements and install dependencies
COPY --chown=node:intelluxe auth_proxy_requirements.txt ./
RUN python3 -m pip install --break-system-packages --upgrade pip setuptools wheel && \
    python3 -m pip install --break-system-packages -r auth_proxy_requirements.txt

# Set working directory
WORKDIR /app

# Copy source files BEFORE building (inside container only)
COPY --chown=node:intelluxe src/ ./src/

# Copy authentication proxy files
COPY --chown=node:intelluxe auth_proxy.py ./
COPY --chown=node:intelluxe start_services.sh ./

# Copy package files first for better caching
COPY --chown=node:intelluxe package*.json ./
COPY --chown=node:intelluxe tsconfig.json ./



# Install dependencies and build
RUN npm install && \
    npm run build && \
    cp src/openapi.json build/ && \
    npm cache clean --force && \
    rm -rf src/ tsconfig.json

# Keep node_modules for production dependencies, only remove source files

# Only the built JavaScript remains in the final image

# Create necessary directories
RUN mkdir -p /app/logs /app/data \
    && chown -R node:intelluxe /app \
    && chmod 755 /app/build /app/logs /app/data \
    && chmod +x /app/start_services.sh

# Switch to non-root user
USER node

# Health check for healthcare service monitoring with security validation  
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Expose auth proxy port
EXPOSE 3001

# Set environment variables
ENV NODE_ENV=production
ENV MCP_SECURITY_MODE=healthcare
ENV PHI_DETECTION_ENABLED=true
ENV AUDIT_LOGGING_LEVEL=comprehensive
ENV HIPAA_COMPLIANCE_MODE=strict

# Security hardening environment variables
ENV NODE_OPTIONS="--max-old-space-size=512"
ENV TMPDIR=/tmp

# Start the healthcare MCP server with authentication proxy
CMD ["/app/start_services.sh"]
