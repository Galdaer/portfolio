# Healthcare MCP Server - Pure stdio mode only
FROM node:20-slim

# Healthcare AI metadata
LABEL maintainer="Intelluxe AI Healthcare Team"
LABEL description="Healthcare MCP server for stdio communication"
LABEL version="1.0.2"

# Security: Create intelluxe group and add node user to it
RUN groupadd -g 1001 intelluxe && usermod -a -G intelluxe node

# Install system utilities for healthchecks and debugging
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    psmisc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY --chown=node:intelluxe package*.json ./
COPY --chown=node:intelluxe tsconfig.json ./

# Copy source files
COPY --chown=node:intelluxe src/ ./src/

# Install dependencies and build
RUN npm install && \
    npm run build && \
    cp src/openapi.json build/ && \
    npm cache clean --force && \
    rm -rf src/ tsconfig.json

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R node:intelluxe /app && \
    chmod -R 755 /app

# Switch to non-root user for security
USER node

# Health check - verify container is responsive 
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD test -f /app/build/index.js && pgrep node > /dev/null || exit 1

# Environment variables
ENV NODE_ENV=production
ENV MCP_TRANSPORT=stdio-only

# Expose port (even though we use stdio, for potential future HTTP endpoints)
EXPOSE 3001

# Start command
CMD ["node", "/app/build/index.js"]
