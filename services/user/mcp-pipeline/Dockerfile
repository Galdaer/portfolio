FROM python:3.12-slim

# Install Node.js for running the MCP server
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create user and group
RUN groupadd -g 1001 intelluxe && \
    useradd -u 1000 -g 1001 -m -s /bin/bash pipeline

WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built MCP server from the healthcare-mcp image
COPY --from=intelluxe/healthcare-mcp:latest /app/build /app/healthcare-mcp
COPY --from=intelluxe/healthcare-mcp:latest /app/package.json /app/healthcare-mcp/
COPY --from=intelluxe/healthcare-mcp:latest /app/node_modules /app/healthcare-mcp/node_modules

# Copy pipeline code
COPY pipelines/ ./pipelines/
COPY start_pipeline.sh .
COPY data/ ./data/

# Update permissions
RUN chown -R pipeline:intelluxe /app && \
    chmod +x start_pipeline.sh

# Create logs directory
RUN mkdir -p /app/logs && chown pipeline:intelluxe /app/logs

USER pipeline

EXPOSE 9099

CMD ["./start_pipeline.sh"]
