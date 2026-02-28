"""
Tests for T6: Feature Engineering — 73 Cardinal flags + 12 custom features + pipeline.
"""

import os
import sqlite3
import tempfile

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_db():
    """Create a temp SQLite DB with 20 sample tenders."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE tenders (
            tender_id TEXT PRIMARY KEY,
            title TEXT,
            buyer_name TEXT,
            buyer_id TEXT,
            value_amount REAL,
            value_currency TEXT,
            procurement_method TEXT,
            procurement_category TEXT,
            status TEXT,
            date_published TEXT,
            date_awarded TEXT,
            npwp_hash TEXT,
            npwp_last4 TEXT,
            total_score REAL,
            year INTEGER,
            source TEXT,
            ingested_at TEXT
        )
    """)
    for i in range(20):
        conn.execute(
            "INSERT INTO tenders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"T{i:04d}",
                f"Tender {i}",
                f"BPBD_{i % 5}",
                f"BUY{i}",
                1_000_000.0 * (i + 1),
                "IDR",
                "open" if i % 3 else "direct penunjukan",
                "konstruksi" if i % 2 else "barang",
                "active",
                f"202{i % 3}-01-{(i % 9) + 1:02d}",
                f"202{i % 3}-03-{(i % 9) + 1:02d}",
                f"abc{i:08x}",
                "1234",
                float(i * 5),
                2020 + (i % 5),
                "opentender",
                "2026-01-01",
            ),
        )
    conn.commit()
    conn.close()
    yield db_path
    os.unlink(db_path)


@pytest.fixture
def empty_db():
    """Create a temp SQLite DB with empty tenders table."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE tenders (
            tender_id TEXT PRIMARY KEY, title TEXT, buyer_name TEXT, buyer_id TEXT,
            value_amount REAL, value_currency TEXT, procurement_method TEXT,
            procurement_category TEXT, status TEXT, date_published TEXT,
            date_awarded TEXT, npwp_hash TEXT, npwp_last4 TEXT,
            total_score REAL, year INTEGER, source TEXT, ingested_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    yield db_path
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Cardinal flags tests
# ---------------------------------------------------------------------------

class TestCardinalFlags:
    def test_shape_73_columns(self, sample_db):
        from backend.features.cardinal_flags import CARDINAL_FLAG_NAMES, compute_cardinal_flags
        df = compute_cardinal_flags(db_path=sample_db)
        assert df.shape[1] == 73, f"Expected 73 cols, got {df.shape[1]}"

    def test_column_names_match(self, sample_db):
        from backend.features.cardinal_flags import CARDINAL_FLAG_NAMES, compute_cardinal_flags
        df = compute_cardinal_flags(db_path=sample_db)
        assert set(df.columns) == set(CARDINAL_FLAG_NAMES)

    def test_index_is_tender_id(self, sample_db):
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(db_path=sample_db)
        assert df.index.name == "tender_id"
        assert "T0000" in df.index

    def test_empty_db_returns_empty_df(self, empty_db):
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(db_path=empty_db)
        assert df.empty
        assert df.shape[1] == 73

    def test_noncompetitive_method_flag(self, sample_db):
        """Tenders with 'penunjukan' method should have R004=1."""
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(db_path=sample_db)
        # Row 0 has method "direct penunjukan"
        assert df.loc["T0000", "R004_non_competitive_method"] == 1.0

    def test_flags_are_float(self, sample_db):
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(db_path=sample_db)
        for col in df.columns:
            non_nan = df[col].dropna()
            assert non_nan.dtype == float or len(non_nan) == 0, \
                f"Column {col} has non-float non-NaN values"

    def test_missing_db_returns_empty_df(self):
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(db_path="/nonexistent/path/db.db")
        assert df.empty
        assert df.shape[1] == 73

    def test_limit_parameter(self, sample_db):
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(db_path=sample_db, limit=5)
        assert len(df) <= 5


# ---------------------------------------------------------------------------
# Custom features tests
# ---------------------------------------------------------------------------

class TestCustomFeatures:
    def test_shape_12_columns(self, sample_db):
        from backend.features.custom_features import CUSTOM_FEATURE_NAMES, compute_custom_features
        df = compute_custom_features(db_path=sample_db)
        assert df.shape[1] == 12, f"Expected 12 cols, got {df.shape[1]}"

    def test_all_feature_names_present(self, sample_db):
        from backend.features.custom_features import CUSTOM_FEATURE_NAMES, compute_custom_features
        df = compute_custom_features(db_path=sample_db)
        for name in CUSTOM_FEATURE_NAMES:
            assert name in df.columns, f"Missing feature: {name}"

    def test_placeholder_features_are_nan(self, sample_db):
        """benford_anomaly and bid_rotation_pattern are placeholders — must be NaN."""
        from backend.features.custom_features import compute_custom_features
        df = compute_custom_features(db_path=sample_db)
        assert bool(df["benford_anomaly"].isna().all()), "benford_anomaly should be NaN"
        assert bool(df["bid_rotation_pattern"].isna().all()), "bid_rotation_pattern should be NaN"

    def test_geographic_concentration_is_nan(self, sample_db):
        """geographic_concentration has no per-bidder region data — must be NaN."""
        from backend.features.custom_features import compute_custom_features
        df = compute_custom_features(db_path=sample_db)
        assert bool(df["geographic_concentration"].isna().all())

    def test_vendor_win_concentration_in_range(self, sample_db):
        """vendor_win_concentration should be [0, 1]."""
        from backend.features.custom_features import compute_custom_features
        df = compute_custom_features(db_path=sample_db)
        col = df["vendor_win_concentration"].dropna()
        assert bool((col >= 0.0).all()) and bool((col <= 1.0).all())

    def test_empty_db_returns_empty_df(self, empty_db):
        from backend.features.custom_features import compute_custom_features
        df = compute_custom_features(db_path=empty_db)
        assert df.empty

    def test_index_is_tender_id(self, sample_db):
        from backend.features.custom_features import compute_custom_features
        df = compute_custom_features(db_path=sample_db)
        assert df.index.name == "tender_id"


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestFeaturePipeline:
    def test_shape_at_least_85_columns(self, sample_db):
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db)
        assert df.shape[1] >= 85, f"Expected ≥85 cols, got {df.shape[1]}"

    def test_metadata_columns_present(self, sample_db):
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db)
        assert "temporal_split" in df.columns
        assert "icw_total_score" in df.columns

    def test_temporal_split_valid_values(self, sample_db):
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db)
        valid_splits = {"train", "val", "test"}
        assert set(df["temporal_split"].unique()).issubset(valid_splits)

    def test_no_duplicate_tender_ids(self, sample_db):
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db)
        assert df.index.duplicated().sum() == 0

    def test_placeholder_features_still_nan(self, sample_db):
        """benford_anomaly + bid_rotation_pattern from pipeline must still be NaN."""
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db)
        assert bool(df["benford_anomaly"].isna().all()), "benford_anomaly should be NaN"
        assert bool(df["bid_rotation_pattern"].isna().all()), "bid_rotation_pattern should be NaN"

    def test_empty_db_returns_empty_df(self, empty_db):
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=empty_db)
        assert df.empty or len(df) == 0

    def test_limit_parameter(self, sample_db):
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db, limit=5)
        assert len(df) <= 5

    def test_save_to_db(self, sample_db):
        """save_to_db=True should write rows to features table."""
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(db_path=sample_db, save_to_db=True)
        conn = sqlite3.connect(sample_db)
        count = conn.execute("SELECT COUNT(*) FROM features").fetchone()[0]
        conn.close()
        assert count == len(df), f"Expected {len(df)} rows in features table, got {count}"

    def test_temporal_split_year_assignment(self, sample_db):
        """Year 2020/2021 → train, 2022 → val, 2023/2024 → test."""
        from backend.features.pipeline import _assign_temporal_split
        assert _assign_temporal_split(2020) == "train"
        assert _assign_temporal_split(2021) == "train"
        assert _assign_temporal_split(2022) == "val"
        assert _assign_temporal_split(2023) == "test"
        assert _assign_temporal_split(2024) == "test"
        assert _assign_temporal_split(None) == "train"
        assert _assign_temporal_split("bad") == "train"
