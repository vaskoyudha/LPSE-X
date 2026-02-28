"""
LPSE-X Feature Engineering Package.

Exports:
    compute_cardinal_flags: 73 OCP red flag indicators
    compute_custom_features: 12 custom forensic ML features
    run_feature_pipeline: Full 85-column feature matrix pipeline
"""

from backend.features.cardinal_flags import compute_cardinal_flags, CARDINAL_FLAG_NAMES
from backend.features.custom_features import compute_custom_features, CUSTOM_FEATURE_NAMES
from backend.features.pipeline import run_feature_pipeline

__all__ = [
    "compute_cardinal_flags",
    "compute_custom_features",
    "run_feature_pipeline",
    "CARDINAL_FLAG_NAMES",
    "CUSTOM_FEATURE_NAMES",
]
