"""LPSE-X Backend — FastAPI entry point."""
import socket
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="LPSE-X API",
    description="Explainable AI for Indonesian Procurement Fraud Detection",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


def find_free_port(start: int = 8000) -> int:
    """Auto-detect free port — no hardcoded port numbers."""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range 8000-8100")


if __name__ == "__main__":
    port = find_free_port()
    print(f"Starting LPSE-X on port {port}")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
