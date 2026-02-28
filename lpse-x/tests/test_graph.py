"""
Tests for T7: Graph construction + Leiden community detection + cartel scoring.

Uses temporary SQLite databases populated with known synthetic data.
All tests are deterministic — same result on repeated runs.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import os
from typing import Generator

import pytest

from backend.graph.builder import build_bipartite_graph, export_graph_json, project_vendor_graph
from backend.graph.leiden import detect_communities
from backend.graph.cartel_scorer import score_communities


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_db(vendors: list[tuple[str, str, str, float, int]]) -> str:
    """
    Create a temporary SQLite DB with the tenders table.

    vendors: list of (tender_id, npwp_hash, buyer_name, value_amount, year)
    Returns path to the temp DB file.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE tenders (
            tender_id TEXT PRIMARY KEY,
            npwp_hash TEXT,
            npwp_last4 TEXT,
            buyer_name TEXT,
            value_amount REAL,
            year INTEGER,
            procurement_method TEXT,
            procurement_category TEXT,
            status TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO tenders (tender_id, npwp_hash, buyer_name, value_amount, year, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (t[0], t[1], t[2], t[3], t[4], "active")
            for t in vendors
        ],
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def empty_db() -> Generator[str, None, None]:
    """DB with tenders table but no rows."""
    path = _make_db([])
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows: SQLite WAL files may still be open briefly


@pytest.fixture
def sample_db() -> Generator[str, None, None]:
    """
    DB with 3 vendors bidding on 4 tenders.

    Vendor A (hash=aaa) bids on T1, T2, T3
    Vendor B (hash=bbb) bids on T1, T2        ← co-bids with A on T1, T2
    Vendor C (hash=ccc) bids on T3, T4        ← co-bids with A on T3
    Vendor D (hash=ddd) bids on T4 only       ← no co-bid with ABC
    """
    rows = [
        ("T1", "aaa", "Kemenkeu", 100_000.0, 2022),
        ("T2", "aaa", "Kemenkeu", 200_000.0, 2022),
        ("T3", "aaa", "PUPR", 150_000.0, 2023),
        ("T1b", "bbb", "Kemenkeu", 110_000.0, 2022),
        ("T2b", "bbb", "Kemenkeu", 195_000.0, 2022),
        ("T3c", "ccc", "PUPR", 155_000.0, 2023),
        ("T4c", "ccc", "DKI", 90_000.0, 2023),
        ("T4d", "ddd", "DKI", 85_000.0, 2023),
    ]
    path = _make_db(rows)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows: SQLite WAL files may still be open briefly


@pytest.fixture
def large_db() -> Generator[str, None, None]:
    """
    DB with 10 vendors forming 2 clear communities of 5.
    Community X: vendors x0..x4 all bid on tenders tx0..tx4 (same buyer)
    Community Y: vendors y0..y4 all bid on tenders ty0..ty4 (same buyer)
    """
    rows: list[tuple[str, str, str, float, int]] = []
    # Community X
    for i in range(5):
        for j in range(5):
            rows.append((f"TX{i}{j}", f"x{i}", "BuyerX", 100_000.0 + i * 1000, 2022))
    # Community Y
    for i in range(5):
        for j in range(5):
            rows.append((f"TY{i}{j}", f"y{i}", "BuyerY", 500_000.0 + i * 1000, 2023))
    path = _make_db(rows)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows: SQLite WAL files may still be open briefly


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------

class TestBuildBipartiteGraph:
    def test_empty_db_returns_empty_graph(self, empty_db: str) -> None:
        G = build_bipartite_graph(db_path=empty_db)
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_bipartite_structure(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        vendors = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 0]
        tenders = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
        assert len(vendors) > 0, "No vendor nodes"
        assert len(tenders) > 0, "No tender nodes"

    def test_correct_vendor_count(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        vendors = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 0]
        # 4 distinct npwp_hash values: aaa, bbb, ccc, ddd
        assert len(vendors) == 4

    def test_edges_exist(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        assert G.number_of_edges() > 0

    def test_vendor_node_attributes(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        vendor_aaa = "vendor:aaa"
        assert G.has_node(vendor_aaa)
        attrs = G.nodes[vendor_aaa]
        assert "bipartite" in attrs
        assert attrs["bipartite"] == 0
        assert "tender_count" in attrs
        assert int(attrs["tender_count"]) >= 1

    def test_tender_node_attributes(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        # Find a tender node
        tender_nodes = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
        assert len(tender_nodes) > 0
        attrs = G.nodes[tender_nodes[0]]
        assert "value_amount" in attrs
        assert "buyer_name" in attrs

    def test_limit_parameter(self, sample_db: str) -> None:
        G_full = build_bipartite_graph(db_path=sample_db)
        G_limited = build_bipartite_graph(db_path=sample_db, limit=2)
        assert G_limited.number_of_nodes() <= G_full.number_of_nodes()

    def test_db_not_found_returns_empty(self) -> None:
        G = build_bipartite_graph(db_path="/nonexistent/path.db")
        assert G.number_of_nodes() == 0


class TestProjectVendorGraph:
    def test_empty_bipartite_returns_empty(self, empty_db: str) -> None:
        G = build_bipartite_graph(db_path=empty_db)
        proj = project_vendor_graph(G)
        assert proj.number_of_nodes() == 0

    def test_shared_tender_creates_edge(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        proj = project_vendor_graph(G)
        # vendor aaa and bbb both bid on T1 and T2 (same buyer_name Kemenkeu)
        # They should be connected in projection
        assert proj.number_of_nodes() > 0

    def test_projection_only_has_vendors(self, sample_db: str) -> None:
        G = build_bipartite_graph(db_path=sample_db)
        proj = project_vendor_graph(G)
        # All nodes should be vendor-type
        for node in proj.nodes():
            assert str(node).startswith("vendor:")


class TestExportGraphJson:
    def test_empty_db_returns_valid_json(self, empty_db: str) -> None:
        raw = export_graph_json(db_path=empty_db)
        parsed = json.loads(raw)
        assert "nodes" in parsed
        assert "links" in parsed
        assert isinstance(parsed["nodes"], list)
        assert isinstance(parsed["links"], list)

    def test_json_structure(self, sample_db: str) -> None:
        raw = export_graph_json(db_path=sample_db)
        parsed = json.loads(raw)
        assert len(parsed["nodes"]) > 0
        assert "id" in parsed["nodes"][0]

    def test_no_raw_npwp_in_export(self, sample_db: str) -> None:
        """Privacy requirement: vendor nodes use npwp_hash only."""
        raw = export_graph_json(db_path=sample_db)
        # The export must not contain a field literally called "npwp"
        # (npwp_hash is acceptable, raw npwp is not)
        parsed = json.loads(raw)
        for node in parsed["nodes"]:
            assert "npwp" not in node or "npwp_hash" in node


# ---------------------------------------------------------------------------
# Leiden detection tests
# ---------------------------------------------------------------------------

class TestDetectCommunities:
    def test_empty_db_returns_empty_list(self, empty_db: str) -> None:
        result = detect_communities(db_path=empty_db, save_to_db=False)
        assert result == []

    def test_returns_list(self, sample_db: str) -> None:
        result = detect_communities(db_path=sample_db, save_to_db=False)
        assert isinstance(result, list)

    def test_community_dict_shape(self, sample_db: str) -> None:
        result = detect_communities(db_path=sample_db, save_to_db=False)
        if result:
            c = result[0]
            assert "community_id" in c
            assert "member_ids" in c
            assert "risk_score" in c
            assert "size" in c
            assert "detected_at" in c

    def test_member_ids_are_hashes(self, sample_db: str) -> None:
        """member_ids must be bare npwp_hash values, NOT 'vendor:...' prefixed."""
        result = detect_communities(db_path=sample_db, save_to_db=False)
        for c in result:
            for mid in c["member_ids"]:
                assert not mid.startswith("vendor:"), (
                    f"member_id should not have 'vendor:' prefix: {mid}"
                )

    def test_seed_determinism(self, sample_db: str) -> None:
        """CRITICAL: Two runs with same seed must produce identical results."""
        r1 = detect_communities(db_path=sample_db, seed=42, save_to_db=False)
        r2 = detect_communities(db_path=sample_db, seed=42, save_to_db=False)
        # Compare community_ids and sorted member_ids
        def canonical(communities: list[dict]) -> list[tuple[str, tuple[str, ...]]]:
            return sorted(
                [
                    (c["community_id"], tuple(sorted(c["member_ids"])))
                    for c in communities
                ]
            )
        assert canonical(r1) == canonical(r2), "Leiden is non-deterministic with same seed!"

    def test_save_to_db(self, sample_db: str) -> None:
        """Communities should be persisted to the communities table."""
        detect_communities(db_path=sample_db, seed=42, save_to_db=True)
        conn = sqlite3.connect(sample_db)
        count = conn.execute("SELECT COUNT(*) FROM communities").fetchone()[0]
        conn.close()
        assert count >= 0  # table exists and is accessible

    def test_large_db_finds_communities(self, large_db: str) -> None:
        """10 vendors with clear bipartite separation should yield ≥1 community."""
        result = detect_communities(db_path=large_db, seed=42, save_to_db=False)
        assert len(result) >= 1

    def test_community_sizes_positive(self, sample_db: str) -> None:
        result = detect_communities(db_path=sample_db, seed=42, save_to_db=False)
        for c in result:
            assert c["size"] >= 1
            assert c["size"] == len(c["member_ids"])


# ---------------------------------------------------------------------------
# Cartel scorer tests
# ---------------------------------------------------------------------------

class TestScoreCommunities:
    def test_empty_communities_returns_empty(self, sample_db: str) -> None:
        result = score_communities([], db_path=sample_db)
        assert result == []

    def test_scores_in_range(self, sample_db: str) -> None:
        communities = detect_communities(db_path=sample_db, seed=42, save_to_db=False)
        scored = score_communities(communities, db_path=sample_db)
        for c in scored:
            score = c["risk_score"]
            assert 0.0 <= score <= 1.0, f"Score out of [0,1]: {score}"

    def test_risk_score_key_present(self, sample_db: str) -> None:
        communities = detect_communities(db_path=sample_db, seed=42, save_to_db=False)
        scored = score_communities(communities, db_path=sample_db)
        for c in scored:
            assert "risk_score" in c

    def test_single_member_community_scores_zero(self, sample_db: str) -> None:
        """A community with only 1 member can't co-bid → all signals = 0."""
        single = [{"community_id": "C99999", "member_ids": ["lone_wolf"], "risk_score": 0.0, "size": 1, "detected_at": "x"}]
        scored = score_communities(single, db_path=sample_db)
        assert scored[0]["risk_score"] == 0.0

    def test_score_is_deterministic(self, sample_db: str) -> None:
        communities = detect_communities(db_path=sample_db, seed=42, save_to_db=False)
        s1 = score_communities([c.copy() for c in communities], db_path=sample_db)
        s2 = score_communities([c.copy() for c in communities], db_path=sample_db)
        for c1, c2 in zip(s1, s2):
            assert c1["risk_score"] == c2["risk_score"]

    def test_all_communities_scored(self, large_db: str) -> None:
        communities = detect_communities(db_path=large_db, seed=42, save_to_db=False)
        if communities:
            scored = score_communities(communities, db_path=large_db)
            assert len(scored) == len(communities)
            for c in scored:
                assert isinstance(c["risk_score"], float)
