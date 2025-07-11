#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE="e2e:latest"
CONTAINER="e2e-test"

# Build image with repository contents
Dockerfile="$SCRIPT_DIR/Dockerfile"

# Build with specific DNS servers and retries
echo "Building e2e test image with network configuration..."
DOCKER_GID=$(getent group docker | cut -d: -f3)
docker build \
    --build-arg http_proxy= \
    --build-arg https_proxy= \
    --build-arg HTTP_PROXY= \
    --build-arg HTTPS_PROXY= \
    --build-arg DOCKER_GID="$DOCKER_GID" \
    --network=host \
    -t "$IMAGE" \
    -f "$Dockerfile" \
    "$REPO_ROOT"

# Launch container and run the test directly
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER$"; then
    docker rm -f "$CONTAINER" >/dev/null
fi

echo "Running e2e test in container..."
docker run --rm --name "$CONTAINER" \
    -e DRY_RUN=true \
    -e CI=true \
    -e SKIP_DOCKER_CHECK=true \
    -e CFG_ROOT=/tmp/test-config \
    -e LOG_DIR=/tmp/test-logs \
    "$IMAGE" \
    bash /workspace/scripts/bootstrap.sh --dry-run --non-interactive

echo "E2E test completed successfully"
