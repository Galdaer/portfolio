#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE="e2e:latest"
CONTAINER="e2e-test"

# Use optimized Dockerfile for faster builds
Dockerfile="$SCRIPT_DIR/Dockerfile.optimized"

# Clean up previous containers
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER$"; then
    echo "Removing previous e2e test container..."
    docker rm -f "$CONTAINER" >/dev/null
fi

# Remove previous image to ensure clean build
if docker images "$IMAGE" -q | grep -q .; then
    echo "Removing previous e2e test image..."
    docker rmi -f "$IMAGE" >/dev/null 2>&1 || true
fi

# Build optimized image with minimal context
echo "Building optimized e2e test image (should be <2 minutes)..."
time docker build \
    --build-arg DOCKER_GID="$(getent group docker | cut -d: -f3)" \
    --progress=plain \
    -t "$IMAGE" \
    -f "$Dockerfile" \
    "$REPO_ROOT"

echo "Image built successfully. Running e2e test in container..."
docker run --rm --name "$CONTAINER" \
    -e DRY_RUN=true \
    -e CI=true \
    -e SKIP_DOCKER_CHECK=true \
    -e CFG_ROOT=/tmp/test-config \
    -e LOG_DIR=/tmp/test-logs \
    "$IMAGE" \
    bash /workspace/scripts/bootstrap.sh --dry-run --non-interactive --skip-docker-check

echo "E2E test completed successfully"
