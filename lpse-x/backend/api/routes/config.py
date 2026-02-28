"""
T14: Config Route
PUT /api/config/inject — dynamic injection (competition-critical)
GET /api/config — current config
GET /api/config/log — audit trail

Re-exports the existing injection router from backend.config.injection.
"""
from backend.config.injection import router  # noqa: F401 — re-export

__all__ = ["router"]
