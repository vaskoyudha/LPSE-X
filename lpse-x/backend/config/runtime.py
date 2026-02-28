"""Runtime configuration loader and singleton."""
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml
from pydantic import BaseModel, Field, field_validator
from enum import Enum

logger = logging.getLogger(__name__)

# Config file path — relative to AppDir (lpse-x/)
_CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "runtime_config.yaml"

class ProcurementScope(str, Enum):
    KONSTRUKSI = "konstruksi"
    BARANG = "barang"
    JASA_KONSULTANSI = "jasa_konsultansi"
    JASA_LAINNYA = "jasa_lainnya"

class AnomalyMethod(str, Enum):
    ISOLATION_FOREST = "isolation_forest"
    XGBOOST = "xgboost"
    ENSEMBLE = "ensemble"

class OutputFormat(str, Enum):
    DASHBOARD = "dashboard"
    API_JSON = "api_json"
    AUDIT_REPORT = "audit_report"

class RuntimeConfig(BaseModel):
    """All 7 competition-mandated injectable parameters."""
    procurement_scope: ProcurementScope = ProcurementScope.KONSTRUKSI
    institution_filter: list[str] = Field(default_factory=list)
    risk_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    year_range: tuple[int, int] = Field(default=(2022, 2024))
    anomaly_method: AnomalyMethod = AnomalyMethod.ENSEMBLE
    output_format: OutputFormat = OutputFormat.DASHBOARD
    custom_params: dict[str, Any] = Field(default_factory=dict)

    @field_validator('risk_threshold')
    @classmethod
    def validate_risk_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"risk_threshold must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator('year_range')
    @classmethod
    def validate_year_range(cls, v: tuple) -> tuple:
        if len(v) != 2 or v[0] > v[1]:
            raise ValueError("year_range must be (start_year, end_year) with start <= end")
        return v

# Thread-safe singleton
_config: Optional[RuntimeConfig] = None
_config_lock = threading.Lock()
_injection_log: list[dict] = []  # Audit trail

def load_config(config_path: Optional[Path] = None) -> RuntimeConfig:
    """Load config from YAML file."""
    path = config_path or _CONFIG_FILE
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        # Convert year_range dict to tuple if needed
        yr = data.get('year_range', {})
        if isinstance(yr, dict):
            data['year_range'] = (yr.get('start', 2022), yr.get('end', 2024))
        # Remove non-injectable internal fields
        injectable_fields = {'procurement_scope', 'institution_filter', 'risk_threshold', 'year_range', 'anomaly_method', 'output_format', 'custom_params'}
        filtered = {k: v for k, v in data.items() if k in injectable_fields}
        return RuntimeConfig(**filtered)
    return RuntimeConfig()

def get_config() -> RuntimeConfig:
    """Get current config singleton. Creates from YAML if not initialized."""
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:
                _config = load_config()
                logger.info("RuntimeConfig initialized from %s", _CONFIG_FILE)
    return _config

def inject_config(updates: dict[str, Any]) -> tuple[dict, dict, list[str]]:
    """Apply partial update. Returns (old_values, new_values, errors)."""
    global _config
    errors = []
    # Ensure config is initialized BEFORE acquiring the lock to avoid deadlock.
    # get_config() also acquires _config_lock on first call.
    get_config()
    with _config_lock:
        current = _config  # _config guaranteed non-None at this point
        old_values = current.model_dump()
        # Merge updates into current
        merged = old_values.copy()
        merged.update(updates)
        try:
            new_config = RuntimeConfig(**merged)
            _config = new_config
            new_values = new_config.model_dump()
            # Audit log
            _injection_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "updates": updates,
                "old_values": old_values,
                "new_values": new_values
            })
            logger.info("Config injected at %s: %s", datetime.utcnow().isoformat(), updates)
            return old_values, new_values, []
        except Exception as e:
            errors.append(str(e))
            return old_values, old_values, errors

def get_injection_log() -> list[dict]:
    """Return audit trail of all injections."""
    return _injection_log.copy()
