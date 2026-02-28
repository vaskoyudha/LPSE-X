"""
LPSE-X Leiden Community Detection.

Converts the NetworkX vendor-vendor projection to igraph format, runs
leidenalg.find_partition with ModularityVertexPartition and a fixed seed
for full reproducibility, then persists communities to SQLite.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

import igraph as ig
import leidenalg

from backend.graph.builder import build_bipartite_graph, project_vendor_graph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_CREATE_COMMUNITIES_TABLE = """
CREATE TABLE IF NOT EXISTS communities (
    community_id  TEXT PRIMARY KEY,
    member_ids    TEXT NOT NULL,          -- JSON array of npwp_hash values
    risk_score    REAL NOT NULL DEFAULT 0.0,
    size          INTEGER NOT NULL DEFAULT 0,
    detected_at   TEXT NOT NULL
)
"""


def _ensure_communities_table(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_COMMUNITIES_TABLE)
    conn.commit()


# ---------------------------------------------------------------------------
# NetworkX → igraph conversion
# ---------------------------------------------------------------------------

def _nx_to_igraph(nx_graph: Any) -> ig.Graph:
    """
    Convert a NetworkX vendor-vendor graph to an igraph.Graph.

    Returns an empty igraph.Graph when input is empty.
    """


    if nx_graph.number_of_nodes() == 0:
        return ig.Graph()

    nodes = list(nx_graph.nodes())
    node_index: dict[str, int] = {n: i for i, n in enumerate(nodes)}

    edges = [
        (node_index[u], node_index[v])
        for u, v in nx_graph.edges()
    ]
    weights = [
        float(nx_graph[u][v].get("weight", 1.0))
        for u, v in nx_graph.edges()
    ]

    g = ig.Graph(n=len(nodes), edges=edges, directed=False)
    g.vs["name"] = nodes          # vertex name = "vendor:{npwp_hash}"
    g.es["weight"] = weights

    return g


# ---------------------------------------------------------------------------
# Community detection
# ---------------------------------------------------------------------------

def detect_communities(
    db_path: str = "data/lpse_x.db",
    limit: int | None = None,
    seed: int = 42,
    save_to_db: bool = True,
) -> list[dict[str, Any]]:
    """
    Run Leiden community detection on the vendor co-bidding graph.

    Args:
        db_path:    Path to SQLite database.
        limit:      Max tenders to load (None = all).
        seed:       RNG seed for reproducibility (default 42, always logged).
        save_to_db: Persist results to ``communities`` table.

    Returns:
        List of community dicts:
          {
            "community_id": str,
            "member_ids": list[str],   # npwp_hash values
            "risk_score": float,
            "size": int,
            "detected_at": str          # ISO-8601 UTC
          }

    Always returns an empty list (not an error) when the DB has no data.
    """
    _leidenalg_ver = getattr(leidenalg, '__version__', 'unknown')
    logger.info(
        "detect_communities: leidenalg=%s igraph=%s seed=%d db=%s",
        _leidenalg_ver,
        ig.__version__,
        seed,
        db_path,
    )

    # Build graphs
    bipartite_g = build_bipartite_graph(db_path=db_path, limit=limit)
    vendor_proj = project_vendor_graph(bipartite_g)

    if vendor_proj.number_of_nodes() == 0:
        logger.info("detect_communities: empty vendor graph — returning [].")
        return []

    # Convert to igraph
    ig_graph = _nx_to_igraph(vendor_proj)
    if ig_graph.vcount() == 0:
        return []

    # Run Leiden with fixed seed
    partition = leidenalg.find_partition(
        ig_graph,
        leidenalg.ModularityVertexPartition,
        weights="weight",
        seed=seed,
    )

    logger.info(
        "detect_communities: %d communities found (modularity=%.4f)",
        len(partition),
        partition.modularity,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    communities: list[dict[str, Any]] = []

    for i, member_indices in enumerate(partition):
        raw_names: list[str] = [
            str(ig_graph.vs[idx]["name"]) for idx in member_indices
        ]
        # Strip "vendor:" prefix to get bare npwp_hash
        member_ids: list[str] = [
            n[len("vendor:"):] if n.startswith("vendor:") else n
            for n in raw_names
        ]
        community_id = f"C{i:05d}"
        communities.append(
            {
                "community_id": community_id,
                "member_ids": member_ids,
                "risk_score": 0.0,   # backfilled by cartel_scorer
                "size": len(member_ids),
                "detected_at": now_iso,
            }
        )

    # Persist to DB
    if save_to_db:
        _save_communities(db_path, communities)

    return communities


def _save_communities(
    db_path: str, communities: list[dict[str, Any]]
) -> None:
    """Upsert community rows into SQLite."""
    try:
        conn = sqlite3.connect(db_path)
        _ensure_communities_table(conn)
        for c in communities:
            conn.execute(
                """
                INSERT INTO communities (community_id, member_ids, risk_score, size, detected_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(community_id) DO UPDATE SET
                    member_ids  = excluded.member_ids,
                    risk_score  = excluded.risk_score,
                    size        = excluded.size,
                    detected_at = excluded.detected_at
                """,
                (
                    c["community_id"],
                    json.dumps(c["member_ids"]),
                    float(c["risk_score"]),
                    int(c["size"]),
                    c["detected_at"],
                ),
            )
        conn.commit()
        conn.close()
        logger.info("detect_communities: saved %d communities to DB.", len(communities))
    except Exception as exc:
        logger.error("detect_communities: DB save failed: %s", exc)
