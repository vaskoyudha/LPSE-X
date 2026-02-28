"""
LPSE-X ONNX Inference Session
================================
Loads ONNX models and runs inference at <200ms per prediction (CPU).

Two inference wrappers:
  - XgboostOnnxSession   — 4-class risk prediction + softmax probabilities
  - IforestOnnxSession   — anomaly score in [0, 1]

Both wrap onnxruntime.InferenceSession and are thread-safe (ORT sessions
are thread-safe for read operations after initialization).

Usage:
    from backend.ml.onnx_inference import XgboostOnnxSession, IforestOnnxSession

    xgb_sess = XgboostOnnxSession("models/xgboost.onnx")
    labels, probs = xgb_sess.predict(X_np)   # X_np: float32 array (n, n_features)

    if_sess = IforestOnnxSession("models/iforest.onnx")
    scores = if_sess.score(X_np)             # returns float32 array (n,) in [0, 1]
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Risk class integer → human-readable label
RISK_LABELS: dict[int, str] = {
    0: "Aman",
    1: "Perlu Pantauan",
    2: "Risiko Tinggi",
    3: "Risiko Kritis",
}


@dataclass
class PredictionResult:
    """Result from XgboostOnnxSession.predict()."""
    labels: np.ndarray                    # shape (n,) int32 0-3
    probabilities: np.ndarray             # shape (n, 4) float32
    risk_names: list[str]                 # human-readable risk level per row
    inference_ms: float                   # wall time in milliseconds


@dataclass
class AnomalyScoreResult:
    """Result from IforestOnnxSession.score()."""
    scores: np.ndarray                    # shape (n,) float32 in [0, 1]
    inference_ms: float


# ---------------------------------------------------------------------------
# XGBoost ONNX Session
# ---------------------------------------------------------------------------
class XgboostOnnxSession:
    """
    Thread-safe ONNX inference session for the XGBoost risk classifier.

    Parameters
    ----------
    onnx_path:
        Path to the xgboost.onnx file.
    """

    def __init__(self, onnx_path: str | Path) -> None:
        import onnxruntime as ort  # type: ignore[import]

        self._path = Path(onnx_path)
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Use all available CPU threads
        sess_options.intra_op_num_threads = 0

        self._session = ort.InferenceSession(
            str(self._path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        # Inspect inputs/outputs
        self._input_name: str = self._session.get_inputs()[0].name
        output_names = [o.name for o in self._session.get_outputs()]
        logger.info(
            "XgboostOnnxSession loaded: %s | input=%s | outputs=%s",
            self._path.name, self._input_name, output_names,
        )

    def predict(self, X: np.ndarray) -> PredictionResult:
        """
        Run inference on X.

        Parameters
        ----------
        X:
            Float32 array of shape (n_samples, n_features).

        Returns
        -------
        PredictionResult with labels, probabilities, risk_names, inference_ms.
        """
        X_f32 = X.astype(np.float32)
        t0 = time.perf_counter()

        outputs = self._session.run(None, {self._input_name: X_f32})

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # XGBoost ONNX outputs: [label (int64), probabilities (float32 map or array)]
        # Output structure may vary by xgboost version — handle both cases
        labels_raw = outputs[0]
        probs_raw = outputs[1]

        labels = np.asarray(labels_raw, dtype=np.int32).ravel()

        # probs_raw might be a list of dicts ({0: p0, 1: p1, ...}) or an ndarray
        if isinstance(probs_raw, np.ndarray):
            probs = probs_raw.astype(np.float32)
        elif isinstance(probs_raw, list) and len(probs_raw) > 0 and isinstance(probs_raw[0], dict):
            # Each element is {class_id: probability}
            n = len(probs_raw)
            n_classes = 4
            probs = np.zeros((n, n_classes), dtype=np.float32)
            for i, d in enumerate(probs_raw):
                for k, v in d.items():
                    probs[i, int(k)] = float(v)
        else:
            # Fallback: reshape whatever we got
            probs = np.asarray(probs_raw, dtype=np.float32).reshape(len(labels), -1)

        risk_names = [RISK_LABELS.get(int(lbl), "Aman") for lbl in labels]

        if elapsed_ms > 200:
            logger.warning(
                "XGBoost ONNX inference SLA breach: %.1fms > 200ms for %d samples",
                elapsed_ms, len(labels),
            )

        logger.debug("XGBoost ONNX inference: %d samples, %.1fms", len(labels), elapsed_ms)
        return PredictionResult(
            labels=labels,
            probabilities=probs,
            risk_names=risk_names,
            inference_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# IsolationForest ONNX Session
# ---------------------------------------------------------------------------
class IforestOnnxSession:
    """
    Thread-safe ONNX inference session for the IsolationForest anomaly detector.

    Parameters
    ----------
    onnx_path:
        Path to the iforest.onnx file.
    """

    def __init__(self, onnx_path: str | Path) -> None:
        import onnxruntime as ort  # type: ignore[import]

        self._path = Path(onnx_path)
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._session = ort.InferenceSession(
            str(self._path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        self._input_name = self._session.get_inputs()[0].name
        output_names = [o.name for o in self._session.get_outputs()]
        logger.info(
            "IforestOnnxSession loaded: %s | input=%s | outputs=%s",
            self._path.name, self._input_name, output_names,
        )

    def score(self, X: np.ndarray) -> AnomalyScoreResult:
        """
        Run anomaly scoring on X.

        Returns anomaly scores normalized to [0, 1] (higher = more anomalous).

        Parameters
        ----------
        X:
            Float32 array of shape (n_samples, n_features).
        """
        X_f32 = X.astype(np.float32)
        t0 = time.perf_counter()

        outputs = self._session.run(None, {self._input_name: X_f32})

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # skl2onnx IsolationForest with score_samples=True outputs raw scores
        # Scores are typically in range (-0.5, 0.5); we negate + normalize
        raw = np.asarray(outputs[-1], dtype=np.float32).ravel()  # last output = scores

        # Negate: more negative raw → more anomalous → higher output
        neg = -raw
        min_s, max_s = float(neg.min()), float(neg.max())
        if max_s > min_s:
            normalized = ((neg - min_s) / (max_s - min_s)).astype(np.float32)
        else:
            normalized = np.zeros_like(neg)

        logger.debug("IForest ONNX scoring: %d samples, %.1fms", len(raw), elapsed_ms)
        return AnomalyScoreResult(scores=normalized, inference_ms=elapsed_ms)
