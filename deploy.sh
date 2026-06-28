#!/usr/bin/env bash
# Deploy script: stop old containers, remove old images, build and start fresh.
# Usage:
#   ./deploy.sh              # default (uses Docker cache for fast builds)
#   ./deploy.sh --ollama     # with local Ollama service
#   ./deploy.sh --no-cache   # force full rebuild (when dependencies change)
#   ./deploy.sh --ollama --no-cache

set -euo pipefail

PROFILE=""
NO_CACHE=""
for arg in "$@"; do
    case "$arg" in
        --ollama)    PROFILE="--profile ollama" ;;
        --no-cache)  NO_CACHE="--no-cache" ;;
        *)           echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

if [[ -n "$PROFILE" ]]; then
    echo ">> Deploying with Ollama profile"
else
    echo ">> Deploying default tradingagents service"
fi

# 1. Stop and remove running containers
echo ">> Stopping running containers..."
docker compose $PROFILE down --remove-orphans

# 2. Remove old images
echo ">> Removing old images..."
docker compose $PROFILE down --rmi local 2>/dev/null || true

# 3. Build new images
echo ">> Building new images..."
docker compose $PROFILE build $NO_CACHE

# 4. Start services in detached mode
echo ">> Starting services..."
docker compose $PROFILE up -d

echo ">> Deploy complete."
docker compose $PROFILE ps
