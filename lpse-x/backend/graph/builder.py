"""
LPSE-X Graph Builder.

Constructs a bipartite NetworkX graph of vendors and tenders from SQLite,
then projects it to a vendor–vendor co-occurrence graph for Leiden detection.

Node types:
  - bipartite=0 → vendor  (identified by npwp_hash)
  - bipartite=1 → tender   (identified by tender_id)

Edges: vendor participated in / won tender.  Edge weight = 1.0 (presence).
The unipartite vendor projection carries edge weight = shared tender count.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

import networkx as nx
from networkx.algorithms import bipartite

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bipartite graph construction
# ---------------------------------------------------------------------------

def build_bipartite_graph(
    db_path: str = "data/lpse_x.db",
    limit: int | None = None,
) -> nx.Graph:
    """
    Build a bipartite NetworkX graph (vendors ↔ tenders) from SQLite.

    Vendor nodes:  bipartite=0, attrs: win_count, tender_count, buyer_name
    Tender nodes:  bipartite=1, attrs: value_amount, buyer_name, year, procurement_method
    Edges:         vendor → tender (weight=1.0)

    Returns an empty graph when the database has no tenders.
    """
    G: nx.Graph = nx.Graph()

    limit_clause = f"LIMIT {limit}" if limit is not None else ""
    query = f"""
        SELECT
            tender_id,
            npwp_hash,
            npwp_last4,
            buyer_name,
            value_amount,
            year,
            procurement_method,
            procurement_category,
            status
        FROM tenders
        WHERE npwp_hash IS NOT NULL
          AND npwp_hash != ''
        {limit_clause}
    """

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(query).fetchall()
        conn.close()
    except Exception as exc:
        logger.error("builder: DB query failed: %s", exc)
        return G

    if not rows:
        logger.info("builder: no tenders with npwp_hash found — returning empty graph.")
        return G

    # Accumulate per-vendor stats
    vendor_stats: dict[str, dict[str, Any]] = {}

    for (
        tender_id,
        npwp_hash,
        _npwp_last4,
        buyer_name,
        value_amount,
        year,
        procurement_method,
        procurement_category,
        status,
    ) in rows:
        # ----- Tender node -----
        tender_node = f"tender:{tender_id}"
        if not G.has_node(tender_node):
            G.add_node(
                tender_node,
                bipartite=1,
                node_type="tender",
                tender_id=str(tender_id),
                buyer_name=str(buyer_name or ""),
                value_amount=float(value_amount) if value_amount is not None else 0.0,
                year=int(year) if year is not None else 0,
                procurement_method=str(procurement_method or ""),
                procurement_category=str(procurement_category or ""),
            )

        # ----- Vendor node -----
        vendor_node = f"vendor:{npwp_hash}"
        if npwp_hash not in vendor_stats:
            vendor_stats[npwp_hash] = {
                "win_count": 0,
                "tender_count": 0,
                "buyer_names": set(),
            }
        vs = vendor_stats[npwp_hash]
        vs["tender_count"] += 1
        if isinstance(status, str) and "award" in status.lower():
            vs["win_count"] += 1
        if buyer_name:
            vs["buyer_names"].add(str(buyer_name))

        if not G.has_node(vendor_node):
            G.add_node(
                vendor_node,
                bipartite=0,
                node_type="vendor",
                npwp_hash=str(npwp_hash),
            )

        # ----- Edge -----
        G.add_edge(vendor_node, tender_node, weight=1.0)

    # Enrich vendor nodes with accumulated stats
    for npwp_hash, vs in vendor_stats.items():
        vendor_node = f"vendor:{npwp_hash}"
        if G.has_node(vendor_node):
            G.nodes[vendor_node]["win_count"] = vs["win_count"]
            G.nodes[vendor_node]["tender_count"] = vs["tender_count"]
            G.nodes[vendor_node]["buyer_name"] = (
                list(vs["buyer_names"])[0] if vs["buyer_names"] else ""
            )

    logger.info(
        "builder: bipartite graph — vendors=%d, tenders=%d, edges=%d",
        sum(1 for _, d in G.nodes(data=True) if d.get("bipartite") == 0),
        sum(1 for _, d in G.nodes(data=True) if d.get("bipartite") == 1),
        G.number_of_edges(),
    )
    return G


# ---------------------------------------------------------------------------
# Vendor-vendor unipartite projection
# ---------------------------------------------------------------------------

def project_vendor_graph(G: nx.Graph) -> nx.Graph:
    """
    Project the bipartite graph onto vendor nodes.

    Edge weight between two vendors = number of shared tenders.
    Returns an empty graph when no vendors exist.
    """
    vendor_nodes: set[Any] = {
        n for n, d in G.nodes(data=True) if d.get("bipartite") == 0
    }
    if not vendor_nodes:
        logger.info("project_vendor_graph: no vendor nodes — returning empty graph.")
        return nx.Graph()

    vendor_proj: nx.Graph = bipartite.weighted_projected_graph(G, vendor_nodes)
    logger.info(
        "project_vendor_graph: vendor nodes=%d, edges=%d",
        vendor_proj.number_of_nodes(),
        vendor_proj.number_of_edges(),
    )
    return vendor_proj


# ---------------------------------------------------------------------------
# JSON export for frontend D3 consumption
# ---------------------------------------------------------------------------

def export_graph_json(
    db_path: str = "data/lpse_x.db",
    limit: int | None = None,
) -> str:
    """
    Build the bipartite graph and export it as a JSON string.

    Schema:
      {
        "nodes": [{"id": str, "type": "vendor"|"tender", ...attrs}],
        "links": [{"source": str, "target": str, "weight": float}]
      }

    Vendor identities use npwp_hash only (privacy requirement).
    """
    G = build_bipartite_graph(db_path=db_path, limit=limit)

    nodes: list[dict[str, Any]] = []
    for node_id, attrs in G.nodes(data=True):
        node_dict: dict[str, Any] = {"id": str(node_id)}
        node_dict.update({k: v for k, v in attrs.items() if k not in ("buyer_names",)})
        nodes.append(node_dict)

    links: list[dict[str, Any]] = [
        {
            "source": str(u),
            "target": str(v),
            "weight": float(data.get("weight", 1.0)),
        }
        for u, v, data in G.edges(data=True)
    ]

    result: dict[str, Any] = {"nodes": nodes, "links": links}
    return json.dumps(result, ensure_ascii=False)
