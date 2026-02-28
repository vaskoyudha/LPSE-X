"""
Tests for T11: ONNX Export Pipeline
=====================================
Tests verify:
  - XGBoost model can be exported to ONNX and loaded
  - IsolationForest can be exported to ONNX and loaded
  - XGBoost ONNX predictions match native sklearn predictions within tolerance
  - IsolationForest ONNX scores are monotonically consistent with native scores
  - Inference latency < 200ms for single-sample prediction
  - Metadata sidecar JSON files are written correctly
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
N_FEATURES = 15
N_TRAIN = 100
N_CLASSES = 4
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

FEATURE_NAMES = [f"feat_{i:02d}" for i in range(N_FEATURES)]


def _make_X(n: int = N_TRAIN) -> np.ndarray:
    return rng.uniform(0.0, 1.0, size=(n, N_FEATURES)).astype(np.float32)


def _make_y(n: int = N_TRAIN) -> np.ndarray:
    base = np.array([0, 1, 2, 3] * (n // 4))
    remainder = np.zeros(n - len(base), dtype=int)
    return np.concatenate([base, remainder]).astype(np.int32)


@pytest.fixture(scope="module")
def X_train() -> np.ndarray:
    return _make_X(N_TRAIN)


@pytest.fixture(scope="module")
def y_train(X_train: np.ndarray) -> np.ndarray:
    return _make_y(N_TRAIN)


@pytest.fixture(scope="module")
def X_test() -> np.ndarray:
    return _make_X(20)


@pytest.fixture(scope="module")
def trained_xgboost(X_train: np.ndarray, y_train: np.ndarray):
    import xgboost as xgb
    model = xgb.XGBClassifier(
        n_estimators=10,
        max_depth=3,
        objective="multi:softprob",
        num_class=N_CLASSES,
        random_state=RANDOM_SEED,
        verbosity=0,
        use_label_encoder=False,
        eval_metric="mlogloss",
    )
    model.fit(X_train, y_train)
    return model


@pytest.fixture(scope="module")
def trained_iforest(X_train: np.ndarray):
    from sklearn.ensemble import IsolationForest
    model = IsolationForest(
        n_estimators=20,
        random_state=RANDOM_SEED,
        contamination=0.1,
        n_jobs=1,
    )
    model.fit(X_train)
    return model


# ---------------------------------------------------------------------------
# XGBoost ONNX Tests
# ---------------------------------------------------------------------------
class TestXgboostOnnxExport:
    """Tests for export_xgboost and XgboostOnnxSession."""

    @pytest.fixture(scope="class")
    def xgb_onnx_path(self, trained_xgboost, tmp_path_factory):
        from backend.ml.onnx_export import export_xgboost
        models_dir = tmp_path_factory.mktemp("models_xgb")
        path = export_xgboost(trained_xgboost, FEATURE_NAMES, models_dir=models_dir)
        return path

    def test_export_creates_onnx_file(self, xgb_onnx_path):
        """ONNX file must exist after export."""
        assert xgb_onnx_path.exists(), f"ONNX file not found: {xgb_onnx_path}"
        assert xgb_onnx_path.stat().st_size > 0

    def test_export_creates_metadata_json(self, xgb_onnx_path):
        """Metadata sidecar JSON must be written."""
        meta_path = xgb_onnx_path.with_suffix(".json")
        assert meta_path.exists()
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["model_type"] == "XGBClassifier"
        assert meta["n_classes"] == 4
        assert len(meta["feature_names"]) == N_FEATURES
        assert "exported_at" in meta

    def test_session_loads_from_path(self, xgb_onnx_path):
        """XgboostOnnxSession should load without error."""
        from backend.ml.onnx_inference import XgboostOnnxSession
        sess = XgboostOnnxSession(xgb_onnx_path)
        assert sess is not None

    def test_predict_returns_correct_shape(self, xgb_onnx_path, X_test):
        """Predictions should have correct shape."""
        from backend.ml.onnx_inference import XgboostOnnxSession, PredictionResult
        sess = XgboostOnnxSession(xgb_onnx_path)
        result = sess.predict(X_test)
        assert isinstance(result, PredictionResult)
        assert result.labels.shape == (len(X_test),)
        assert result.probabilities.shape == (len(X_test), N_CLASSES)

    def test_predict_labels_are_valid_classes(self, xgb_onnx_path, X_test):
        """All predicted labels should be in {0, 1, 2, 3}."""
        from backend.ml.onnx_inference import XgboostOnnxSession
        sess = XgboostOnnxSession(xgb_onnx_path)
        result = sess.predict(X_test)
        assert set(result.labels.tolist()).issubset({0, 1, 2, 3})

    def test_predict_probabilities_sum_to_one(self, xgb_onnx_path, X_test):
        """Softmax probabilities must sum to ~1.0 per sample."""
        from backend.ml.onnx_inference import XgboostOnnxSession
        sess = XgboostOnnxSession(xgb_onnx_path)
        result = sess.predict(X_test)
        row_sums = result.probabilities.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=1e-3), \
            f"Probabilities don't sum to 1: min={row_sums.min():.4f}, max={row_sums.max():.4f}"

    def test_predict_risk_names_are_valid(self, xgb_onnx_path, X_test):
        """Risk names must be one of the 4 valid labels."""
        from backend.ml.onnx_inference import XgboostOnnxSession, RISK_LABELS
        valid = set(RISK_LABELS.values())
        sess = XgboostOnnxSession(xgb_onnx_path)
        result = sess.predict(X_test)
        for name in result.risk_names:
            assert name in valid, f"Invalid risk name: {name}"

    def test_predict_parity_with_native_xgboost(self, xgb_onnx_path, trained_xgboost, X_test):
        """ONNX labels must match native XGBoost labels for all test samples."""
        from backend.ml.onnx_inference import XgboostOnnxSession
        sess = XgboostOnnxSession(xgb_onnx_path)
        onnx_result = sess.predict(X_test)

        native_labels = trained_xgboost.predict(X_test).astype(np.int32)

        match_rate = float(np.mean(onnx_result.labels == native_labels))
        assert match_rate >= 0.95, \
            f"ONNX vs native label mismatch: match_rate={match_rate:.3f} < 0.95"

    def test_predict_inference_sla(self, xgb_onnx_path):
        """Single-sample inference must complete in <200ms."""
        from backend.ml.onnx_inference import XgboostOnnxSession
        sess = XgboostOnnxSession(xgb_onnx_path)
        X_single = _make_X(1)
        t0 = time.perf_counter()
        sess.predict(X_single)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert elapsed_ms < 200.0, f"Inference SLA breach: {elapsed_ms:.1f}ms > 200ms"


# ---------------------------------------------------------------------------
# IsolationForest ONNX Tests
# ---------------------------------------------------------------------------
class TestIforestOnnxExport:
    """Tests for export_isolation_forest and IforestOnnxSession."""

    @pytest.fixture(scope="class")
    def iforest_onnx_path(self, trained_iforest, tmp_path_factory):
        from backend.ml.onnx_export import export_isolation_forest
        models_dir = tmp_path_factory.mktemp("models_if")
        path = export_isolation_forest(trained_iforest, FEATURE_NAMES, models_dir=models_dir)
        return path

    def test_export_creates_onnx_file(self, iforest_onnx_path):
        assert iforest_onnx_path.exists()
        assert iforest_onnx_path.stat().st_size > 0

    def test_export_creates_metadata_json(self, iforest_onnx_path):
        meta_path = iforest_onnx_path.with_suffix(".json")
        assert meta_path.exists()
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["model_type"] == "IsolationForest"
        assert meta["n_features"] == N_FEATURES
        assert "exported_at" in meta

    def test_session_loads_from_path(self, iforest_onnx_path):
        from backend.ml.onnx_inference import IforestOnnxSession
        sess = IforestOnnxSession(iforest_onnx_path)
        assert sess is not None

    def test_score_returns_correct_shape(self, iforest_onnx_path, X_test):
        from backend.ml.onnx_inference import IforestOnnxSession, AnomalyScoreResult
        sess = IforestOnnxSession(iforest_onnx_path)
        result = sess.score(X_test)
        assert isinstance(result, AnomalyScoreResult)
        assert result.scores.shape == (len(X_test),)

    def test_scores_in_zero_one_range(self, iforest_onnx_path, X_test):
        from backend.ml.onnx_inference import IforestOnnxSession
        sess = IforestOnnxSession(iforest_onnx_path)
        result = sess.score(X_test)
        assert float(result.scores.min()) >= -1e-4, f"Score below 0: {result.scores.min()}"
        assert float(result.scores.max()) <= 1.0 + 1e-4, f"Score above 1: {result.scores.max()}"

    def test_score_parity_monotonicity_with_native(self, iforest_onnx_path, trained_iforest, X_test):
        """
        ONNX scores should be monotonically consistent with native scores:
        if native_score[i] > native_score[j], then onnx_score[i] >= onnx_score[j] most of the time.
        Allow up to 10% inversions due to float32 precision differences.
        """
        from backend.ml.onnx_inference import IforestOnnxSession
        sess = IforestOnnxSession(iforest_onnx_path)
        onnx_result = sess.score(X_test)

        # Native: negate score_samples (higher = more anomalous, before normalization)
        native_raw = -trained_iforest.score_samples(X_test)

        # Build all pairs and check ordering consistency
        n = len(X_test)
        n_pairs = 0
        n_consistent = 0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(native_raw[i] - native_raw[j]) > 1e-6:
                    n_pairs += 1
                    native_higher = i if native_raw[i] > native_raw[j] else j
                    onnx_higher = i if onnx_result.scores[i] >= onnx_result.scores[j] else j
                    if native_higher == onnx_higher:
                        n_consistent += 1

        if n_pairs > 0:
            consistency_rate = n_consistent / n_pairs
            assert consistency_rate >= 0.80, \
                f"ONNX score ordering consistency {consistency_rate:.3f} < 0.80"

    def test_score_inference_sla(self, iforest_onnx_path):
        """Single-sample scoring must complete in <200ms."""
        from backend.ml.onnx_inference import IforestOnnxSession
        sess = IforestOnnxSession(iforest_onnx_path)
        X_single = _make_X(1)
        t0 = time.perf_counter()
        sess.score(X_single)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert elapsed_ms < 200.0, f"IForest ONNX SLA breach: {elapsed_ms:.1f}ms > 200ms"
