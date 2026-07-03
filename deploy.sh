#!/usr/bin/env bash
# Deploy script: build and start services while preserving hot Docker cache.
# Usage:
#   ./deploy.sh              # default (uses Docker cache for fast builds)
#   ./deploy.sh --ollama     # with local Ollama service
#   ./deploy.sh --external-worker  # API + worker split
#   ./deploy.sh --no-cache   # force full rebuild (when dependencies change)
#   ./deploy.sh --deep-clean # also prune unused Docker build cache after deploy
#   ./deploy.sh --ollama --external-worker --no-cache --deep-clean
#
# Optional:
#   TRADINGAGENTS_DOCKER_BUILD_CACHE_MAX_USED_SPACE=5GB

set -euo pipefail

COMPOSE_ARGS=()
ENV_VARS=()
BUILD_ARGS=()
PRUNE_BUILD_CACHE=0
BUILD_CACHE_MAX_USED_SPACE="${TRADINGAGENTS_DOCKER_BUILD_CACHE_MAX_USED_SPACE:-5GB}"
USE_OLLAMA=0
USE_EXTERNAL_WORKER=0
for arg in "$@"; do
    case "$arg" in
        --ollama)
            COMPOSE_ARGS+=(--profile ollama)
            ENV_VARS+=("TRADINGAGENTS_LLM_PROVIDER=ollama")
            ENV_VARS+=("OLLAMA_BASE_URL=http://ollama:11434/v1")
            USE_OLLAMA=1
            ;;
        --external-worker)
            COMPOSE_ARGS+=(--profile external-worker)
            ENV_VARS+=("TRADINGAGENTS_WEB_RUN_MODE=external_worker")
            ENV_VARS+=("TRADINGAGENTS_WEB_STATE_BACKEND=sqlite")
            USE_EXTERNAL_WORKER=1
            ;;
        --no-cache)
            BUILD_ARGS+=(--no-cache)
            ;;
        --deep-clean|--prune-build-cache)
            PRUNE_BUILD_CACHE=1
            ;;
        *)           echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

run_compose() {
    local cmd=(docker compose)
    if ((${#COMPOSE_ARGS[@]})); then
        cmd+=("${COMPOSE_ARGS[@]}")
    fi
    cmd+=("$@")

    if ((${#ENV_VARS[@]})); then
        env "${ENV_VARS[@]}" "${cmd[@]}"
    else
        "${cmd[@]}"
    fi
}

if ((USE_EXTERNAL_WORKER)); then
    echo ">> Deploying split API + worker services"
elif ((USE_OLLAMA)); then
    echo ">> Deploying with Ollama profile"
else
    echo ">> Deploying default tradingagents service"
fi

# Build and start services. The default path keeps existing containers alive
# until the replacement image is ready and preserves Docker's build cache.
if ((${#BUILD_ARGS[@]})); then
    echo ">> Building new images without cache..."
    run_compose build "${BUILD_ARGS[@]}"
    echo ">> Starting services..."
    run_compose up -d --no-build --remove-orphans
else
    echo ">> Building and starting services..."
    run_compose up -d --build --remove-orphans
fi

echo ">> Pruning dangling Docker images..."
docker image prune -f

if ((PRUNE_BUILD_CACHE)); then
    echo ">> Pruning unused Docker build cache..."
    docker builder prune -af
else
    echo ">> Keeping Docker build cache under ${BUILD_CACHE_MAX_USED_SPACE}..."
    docker builder prune -f --max-used-space "$BUILD_CACHE_MAX_USED_SPACE"
fi

echo ">> Deploy complete."
run_compose ps
