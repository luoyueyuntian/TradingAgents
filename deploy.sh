#!/usr/bin/env bash
# Deploy script: stop old containers, remove old images, build and start fresh.
# Usage:
#   ./deploy.sh              # default (uses Docker cache for fast builds)
#   ./deploy.sh --ollama     # with local Ollama service
#   ./deploy.sh --external-worker  # API + worker split
#   ./deploy.sh --no-cache   # force full rebuild (when dependencies change)
#   ./deploy.sh --ollama --external-worker --no-cache

set -euo pipefail

COMPOSE_ARGS=()
ENV_VARS=()
BUILD_ARGS=()
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

# 1. Stop and remove running containers
echo ">> Stopping running containers..."
run_compose down --remove-orphans

# 2. Remove old images
echo ">> Removing old images..."
run_compose down --rmi local 2>/dev/null || true

# 3. Build new images
echo ">> Building new images..."
if ((${#BUILD_ARGS[@]})); then
    run_compose build "${BUILD_ARGS[@]}"
else
    run_compose build
fi

# 4. Start services in detached mode
echo ">> Starting services..."
run_compose up -d

echo ">> Deploy complete."
run_compose ps
