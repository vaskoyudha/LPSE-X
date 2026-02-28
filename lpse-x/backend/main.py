"""
LPSE-X Backend — FastAPI application factory.

T14: Full router registration:
  - /api/health        (GET)         — health + uptime + model status
  - /api/config        (GET/PUT)     — runtime config injection (Dynamic Injection)
  - /api/predict       (POST)        — ensemble risk prediction
  - /api/xai/{id}      (POST)        — Oracle Sandwich 5-layer XAI
  - /api/xai/dice/*    (POST/GET)    — DiCE background precompute + status
  - /api/graph         (GET)         — Leiden vendor communities
  - /api/reports/{id}  (GET/POST)    — IIA 2025-format report generation

Design rules (from AGENTS.md):
  - No fixed port numbers — auto-detect with find_free_port()
  - No hardcoded parameters — everything via runtime_config.yaml
  - Fully offline — no external API calls
"""
from __future__ import annotations


import pathlib

import logging
import socket

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import config_router
from backend.api.routes import health, inference, xai, graph, reports

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LPSE-X API",
    description=(
        "Explainable AI for Indonesian Procurement Fraud Detection. "
        "Track C: XAI — The Explainable Oracle — Find IT! 2026 at UGM."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — open for local React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router registration (order matters — specific before wildcard)
# ---------------------------------------------------------------------------

# Dynamic Injection endpoint (COMPETITION-CRITICAL)
app.include_router(config_router)           # /api/config GET, PUT /inject, GET /log

# Core API routes
app.include_router(health.router)           # /api/health GET
app.include_router(inference.router)        # /api/predict POST
app.include_router(xai.router)              # /api/xai/* POST/GET
app.include_router(graph.router)            # /api/graph GET, /api/graph/vendor/{id} GET
app.include_router(reports.router)          # /api/reports/{id} GET/POST


# ---------------------------------------------------------------------------
# Static frontend — serve dist/ if built (offline-capable single-process mode)
# ---------------------------------------------------------------------------

_DIST_DIR = pathlib.Path(__file__).parent.parent / "frontend" / "dist"
if _DIST_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    # Mount AFTER all /api routes so they take priority
    app.mount("/", StaticFiles(directory=str(_DIST_DIR), html=True), name="frontend")
    logger.info("Serving frontend from %s", _DIST_DIR)


# ---------------------------------------------------------------------------
# Port auto-detection — never hardcode port numbers (AGENTS.md rule)
# ---------------------------------------------------------------------------

def find_free_port(start: int = 8000) -> int:
    """
    Auto-detect a free TCP port starting from `start`.
    Scans 8000–8099 and returns the first available port.
    Raises RuntimeError if all ports in range are occupied.
    """
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}–{start + 99}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    port = find_free_port()
    logger.info("Starting LPSE-X API on port %d", port)
    print(f"🚀 LPSE-X starting on http://localhost:{port}")
    print(f"   App:     http://localhost:{port}/")
    print(f"   API:     http://localhost:{port}/docs")
    if _DIST_DIR.exists():
        print(f"   (Frontend served from {_DIST_DIR})")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
