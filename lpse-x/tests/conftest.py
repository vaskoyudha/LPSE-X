"""Pytest configuration for LPSE-X tests."""
import pytest


@pytest.fixture
def sample_config() -> dict[str, object]:
    """Sample runtime config for tests."""
    return {
        "procurement_scope": "konstruksi",
        "institution_filter": [],
        "risk_threshold": 0.65,
        "year_range": {"start": 2022, "end": 2024},
        "anomaly_method": "ensemble",
        "output_format": "dashboard",
        "custom_params": {},
    }
