#!/usr/bin/env python3
"""
LPSE-X Startup Launcher (T20 — Offline Bundle)

Single-command startup:
    python start_lpse_x.py

What it does:
  1. Verifies the virtual environment is active (or locates .venv)
  2. Checks that the frontend dist/ is built
  3. Auto-detects a free port (8000–8099)
  4. Starts uvicorn serving both API + frontend static files
  5. Opens the browser automatically

Design rules (AGENTS.md):
  - No fixed port numbers
  - No external API calls
  - Fully offline-capable
"""
from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import time
import webbrowser


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).parent
FRONTEND_DIST = ROOT / "frontend" / "dist"
VENV_PYTHON_WIN = ROOT / ".venv" / "Scripts" / "python.exe"
VENV_PYTHON_UNIX = ROOT / ".venv" / "bin" / "python"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_free_port(start: int = 8000) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}–{start + 99}")


def resolve_python() -> str:
    """Return the Python executable to use — prefer venv, fallback to sys.executable."""
    if VENV_PYTHON_WIN.exists():
        return str(VENV_PYTHON_WIN)
    if VENV_PYTHON_UNIX.exists():
        return str(VENV_PYTHON_UNIX)
    # Already inside a venv
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        return sys.executable
    print("⚠  Could not find .venv — using system Python (may be missing deps)")
    return sys.executable


def check_frontend_built() -> bool:
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        print(f"⚠  Frontend dist not found at {FRONTEND_DIST}")
        print("   Run: cd frontend && npm run build")
        print("   Or:  node_modules/.bin/vite build")
        return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  LPSE-X — Explainable Procurement Fraud Analytics")
    print("  Find IT! 2026 at UGM — Track C: XAI")
    print("=" * 60)

    python_exe = resolve_python()
    print(f"\n  Python: {python_exe}")

    if not check_frontend_built():
        print("\n  Starting API-only mode (no frontend)...")
    else:
        print(f"  Frontend: {FRONTEND_DIST}")

    port = find_free_port()
    print(f"\n  Port:    {port}")
    print(f"  App:     http://localhost:{port}/")
    print(f"  API:     http://localhost:{port}/docs")
    print("\n  Press Ctrl+C to stop\n")
    print("=" * 60)

    # Build the uvicorn command
    cmd = [
        python_exe, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--no-access-log",
    ]

    env = os.environ.copy()
    # Ensure the project root is on PYTHONPATH so `import backend` works
    python_path = env.get("PYTHONPATH", "")
    root_str = str(ROOT)
    if root_str not in python_path:
        env["PYTHONPATH"] = root_str + os.pathsep + python_path if python_path else root_str

    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)

    # Wait briefly then open browser
    time.sleep(2)
    url = f"http://localhost:{port}/"
    try:
        webbrowser.open(url)
        print(f"  Browser opened: {url}")
    except Exception:
        print(f"  Open manually:  {url}")

    # Wait for process
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n\n  Shutting down LPSE-X...")
        proc.terminate()
        proc.wait()
        print("  Stopped. Bye!")


if __name__ == "__main__":
    main()
