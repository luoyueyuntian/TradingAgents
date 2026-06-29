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
NO_CACHE=""
for arg in "$@"; do
    case "$arg" in
        --ollama)
            COMPOSE_ARGS+=(--profile ollama)
            ENV_VARS+=("TRADINGAGENTS_LLM_PROVIDER=ollama")
            ENV_VARS+=("OLLAMA_BASE_URL=http://ollama:11434/v1")
            ;;
        --external-worker)
            COMPOSE_ARGS+=(--profile external-worker)
            ENV_VARS+=("TRADINGAGENTS_WEB_RUN_MODE=external_worker")
            ENV_VARS+=("TRADINGAGENTS_WEB_STATE_BACKEND=sqlite")
            ;;
        --no-cache)  NO_CACHE="--no-cache" ;;
        *)           echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

if [[ " ${COMPOSE_ARGS[*]} " == *" --profile external-worker "* ]]; then
    echo ">> Deploying split API + worker services"
elif [[ " ${COMPOSE_ARGS[*]} " == *" --profile ollama "* ]]; then
    echo ">> Deploying with Ollama profile"
else
    echo ">> Deploying default tradingagents service"
fi

# 1. Stop and remove running containers
echo ">> Stopping running containers..."
env "${ENV_VARS[@]}" docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans

# 2. Remove old images
echo ">> Removing old images..."
env "${ENV_VARS[@]}" docker compose "${COMPOSE_ARGS[@]}" down --rmi local 2>/dev/null || true

# 3. Build new images
echo ">> Building new images..."
env "${ENV_VARS[@]}" docker compose "${COMPOSE_ARGS[@]}" build $NO_CACHE

# 4. Start services in detached mode
echo ">> Starting services..."
env "${ENV_VARS[@]}" docker compose "${COMPOSE_ARGS[@]}" up -d

echo ">> Deploy complete."
env "${ENV_VARS[@]}" docker compose "${COMPOSE_ARGS[@]}" ps
