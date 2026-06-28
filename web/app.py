"""FastAPI application for TradingAgents Web."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import router

app = FastAPI(
    title="TradingAgents Web",
    description="Multi-Agents LLM Financial Trading Framework - Web Interface",
    version="0.1.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
from pathlib import Path

_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Include API routes
app.include_router(router)
