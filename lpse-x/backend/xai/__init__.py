"""
LPSE-X XAI Package
==================
Oracle Sandwich 5-layer explainability architecture:
  Layer 1: SHAP (Global Feature Importance — TreeSHAP for XGBoost)
  Layer 2: DiCE (Local Counterfactuals — cached/async, not blocking)
  Layer 3: Anchors (Rule Extraction — alibi AnchorTabular)
  Layer 4: Leiden (Graph Community Detection — imported from graph module)
  Layer 5: Benford (Statistical Forensics — imported from analysis module)
"""
from backend.xai.shap_explainer import (
    ShapGlobalResult,
    ShapLocalResult,
    compute_shap_global,
    compute_shap_local,
)
from backend.xai.anchor_explainer import (
    AnchorResult,
    compute_anchors,
)
from backend.xai.oracle_sandwich import (
    OracleSandwichResult,
    LayerResult,
    explain_tender,
)
from backend.xai.dice_explainer import (
    CounterfactualResult,
    DiceExplainer,
)
from backend.xai.dice_cache import DiceCacheManager
__all__ = [
    "ShapGlobalResult",
    "ShapLocalResult",
    "compute_shap_global",
    "compute_shap_local",
    "AnchorResult",
    "compute_anchors",
    "OracleSandwichResult",
    "LayerResult",
    "explain_tender",
    "CounterfactualResult",
    "DiceExplainer",
    "DiceCacheManager",
]
