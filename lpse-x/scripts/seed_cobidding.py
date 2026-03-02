"""
LPSE-X Co-Bidding Community Seeder
=====================================
Creates synthetic multi-vendor graph communities by grouping vendors
that share the same buyer_name (same-buyer = potential co-bidders).

This script DIRECTLY inserts into the communities table without re-running
Leiden (pointless since each tender has only 1 vendor → zero shared edges).

Run from project root:
    .venv/Scripts/python.exe scripts/seed_cobidding.py
"""
from __future__ import annotations

import json
import random
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = "data/lpse_x.db"

# Reproducibility
random.seed(42)


def main() -> None:
    print("=== LPSE-X Co-Bidding Community Seeder ===")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Query all vendors grouped by buyer_name (same buyer = potential co-bidders)
    buyer_vendors: dict[str, list[str]] = {}
    rows = conn.execute(
        """
        SELECT buyer_name, npwp_hash
        FROM tenders
        WHERE npwp_hash IS NOT NULL AND npwp_hash != ''
        GROUP BY buyer_name, npwp_hash
        ORDER BY buyer_name
        """
    ).fetchall()

    for row in rows:
        buyer = row["buyer_name"]
        npwp = row["npwp_hash"]
        if buyer not in buyer_vendors:
            buyer_vendors[buyer] = []
        buyer_vendors[buyer].append(npwp)

    # Filter to buyers with 2+ vendors, sorted by vendor count descending
    qualifying: list[tuple[str, list[str]]] = sorted(
        [(buyer, vendors) for buyer, vendors in buyer_vendors.items() if len(vendors) >= 2],
        key=lambda x: len(x[1]),
        reverse=True,
    )
    print(f"Buyers with 2+ vendors: {len(qualifying)}")

    # Build 8 synthetic communities from the top qualifying buyers
    # Use up to 4 vendors per community for variety
    communities: list[dict] = []
    detected_at = datetime.now(timezone.utc).isoformat()

    target_count = min(8, len(qualifying))
    for i in range(target_count):
        buyer, vendors = qualifying[i]
        # Take a random subset of size 2-4
        max_size = min(4, len(vendors))
        size = random.randint(2, max_size) if max_size >= 2 else 2
        # Shuffle then slice (seed=42 already set)
        shuffled = vendors.copy()
        random.shuffle(shuffled)
        members = shuffled[:size]

        community_id = f"cobid-{uuid.UUID(int=random.getrandbits(128)).hex[:8]}"
        # Risk score: random between 0.40 and 0.90
        risk_score = round(random.uniform(0.40, 0.90), 4)

        communities.append(
            {
                "community_id": community_id,
                "member_ids": json.dumps(members),
                "risk_score": risk_score,
                "detected_at": detected_at,
                "size": size,
            }
        )

        print(f"  Community {community_id}: {size} vendors from '{buyer}' (risk={risk_score:.4f})")

    # Delete ALL existing communities (all size=1, useless for demo)
    deleted = conn.execute("DELETE FROM communities").rowcount
    print(f"\nDeleted {deleted} existing communities (all were size=1)")

    # Insert new multi-vendor communities
    conn.executemany(
        "INSERT INTO communities (community_id, member_ids, risk_score, detected_at, size) "
        "VALUES (:community_id, :member_ids, :risk_score, :detected_at, :size)",
        communities,
    )
    conn.commit()
    conn.close()

    # Summary
    print(f"\n=== Seeding Summary ===")
    print(f"Communities inserted: {len(communities)}")
    size_ge2 = sum(1 for c in communities if c["size"] >= 2)
    size_ge3 = sum(1 for c in communities if c["size"] >= 3)
    print(f"  size >= 2: {size_ge2}")
    print(f"  size >= 3: {size_ge3}")
    print(f"\nDone. communities table now has {len(communities)} rows (all multi-vendor).")


if __name__ == "__main__":
    main()
