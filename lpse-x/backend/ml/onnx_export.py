"""
LPSE-X ONNX Export Pipeline
=============================
Exports trained ML models to ONNX format for <200ms CPU inference.

Supported models:
  - XGBoost multiclass classifier → onnxmltools.convert_xgboost
  - IsolationForest (sklearn)      → skl2onnx convert_sklearn with bool→int monkey-patch

Usage:
    from backend.ml.onnx_export import export_xgboost, export_isolation_forest

Notes:
  - XGBoost native model.save_model(".onnx") saves UBJSON (not real ONNX protobuf) — unusable
  - skl2onnx has no built-in XGBClassifier converter → use onnxmltools which extends skl2onnx
  - IsolationForest requires target_opset {"": 15, "ai.onnx.ml": 2} (converter requires ml>=2)
  - skl2onnx 1.17 bug: IsolationForest converter passes Python bool for INT fields in ONNX
    protobuf → monkey-patch onnx.helper.make_attribute to cast bool→int during conversion
  - Feature names and metadata are written to a sidecar JSON file
  - All exported files land in `models/` directory (relative to AppDir)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODELS_DIR = Path("models")


def _ensure_models_dir(models_dir: Path) -> None:
    models_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# XGBoost → ONNX (via onnxmltools)
# ---------------------------------------------------------------------------
def export_xgboost(
    model: Any,
    feature_names: list[str],
    output_path: Path | None = None,
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> Path:
    """
    Export a fitted XGBClassifier to ONNX via onnxmltools.

    onnxmltools extends skl2onnx with an XGBoost converter that produces valid
    ONNX protobuf (not UBJSON).  The resulting ONNX model outputs:
      [0]  label         shape (n,)   int64  — predicted class index 0-3
      [1]  probabilities shape (n, 4) float32 — softmax class probabilities

    Parameters
    ----------
    model:
        Fitted xgboost.XGBClassifier.
    feature_names:
        List of feature column names (stored in metadata sidecar JSON).
    output_path:
        Full path for output file. Defaults to models/xgboost.onnx.
    models_dir:
        Directory for output. Used when output_path is None.

    Returns
    -------
    Path to the saved ONNX file.
    """
    from onnxmltools import convert_xgboost  # type: ignore[import]
    from onnxmltools.convert.common.data_types import FloatTensorType  # type: ignore[import]

    _ensure_models_dir(models_dir)
    if output_path is None:
        output_path = models_dir / "xgboost.onnx"

    n_features = len(feature_names)
    initial_type = [("float_input", FloatTensorType([None, n_features]))]

    onnx_model = convert_xgboost(model, initial_types=initial_type)

    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    # Write metadata sidecar JSON
    meta: dict[str, Any] = {
        "model_type": "XGBClassifier",
        "feature_names": feature_names,
        "n_features": n_features,
        "n_classes": 4,
        "risk_labels": ["Aman", "Perlu Pantauan", "Risiko Tinggi", "Risiko Kritis"],
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "onnx_path": str(output_path),
        "export_method": "onnxmltools",
    }
    meta_path = output_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    logger.info("XGBoost → ONNX exported to %s (metadata: %s)", output_path, meta_path)
    return output_path


# ---------------------------------------------------------------------------
# IsolationForest → ONNX (via skl2onnx + bool→int monkey-patch)
# ---------------------------------------------------------------------------
def export_isolation_forest(
    model: Any,
    feature_names: list[str],
    output_path: Path | None = None,
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> Path:
    """
    Export a fitted IsolationForest to ONNX via skl2onnx.

    skl2onnx 1.17 bug: the IsolationForest converter passes Python ``bool``
    values for INT fields in the ONNX protobuf, causing a ``TypeError`` at
    serialisation time.  We monkey-patch ``onnx.helper.make_attribute`` to
    cast bool→int in list values only during the conversion call, then restore
    the original function.

    The converter also requires ``ai.onnx.ml`` opset ≥ 2 (it raises
    ``RuntimeError`` for opset 1).  We use
    ``target_opset={"": 15, "ai.onnx.ml": 2}``.

    ONNX outputs (after loading with onnxruntime):
      [0]  label  shape (n, 1) int64  — 1 = normal, -1 = anomaly
      [1]  scores shape (n, 1) float32 — raw scores: positive = normal, negative = anomaly
           Normalise to [0, 1] anomaly score by negating then min-max scaling.

    Parameters
    ----------
    model:
        Fitted sklearn.ensemble.IsolationForest.
    feature_names:
        List of feature column names (stored in metadata sidecar JSON).
    output_path:
        Full path for output file. Defaults to models/iforest.onnx.
    models_dir:
        Directory for output. Used when output_path is None.

    Returns
    -------
    Path to the saved ONNX file.
    """
    import onnx.helper as _onnx_helper  # type: ignore[import]
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    _ensure_models_dir(models_dir)
    if output_path is None:
        output_path = models_dir / "iforest.onnx"

    n_features = len(feature_names)
    initial_type = [("float_input", FloatTensorType([None, n_features]))]

    # Monkey-patch: cast bool→int in list attributes during IForest conversion
    _orig_make_attribute = _onnx_helper.make_attribute

    def _patched_make_attribute(key: str, value: Any, doc_string: str | None = None, attr_type: Any = None) -> Any:  # noqa: ANN401
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], bool):
            value = [int(v) for v in value]
        return _orig_make_attribute(key, value, doc_string=doc_string, attr_type=attr_type)

    _onnx_helper.make_attribute = _patched_make_attribute
    try:
        onnx_model = convert_sklearn(
            model,
            initial_types=initial_type,
            target_opset={"": 15, "ai.onnx.ml": 2},
        )
    finally:
        # Always restore the original function
        _onnx_helper.make_attribute = _orig_make_attribute

    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    # Write metadata sidecar JSON
    meta: dict[str, Any] = {
        "model_type": "IsolationForest",
        "feature_names": feature_names,
        "n_features": n_features,
        "score_output": "anomaly_score_0_to_1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "onnx_path": str(output_path),
        "export_method": "skl2onnx_bool_patched",
        "target_opset": {"": 15, "ai.onnx.ml": 2},
    }
    meta_path = output_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    logger.info("IsolationForest → ONNX exported to %s (metadata: %s)", output_path, meta_path)
    return output_path
