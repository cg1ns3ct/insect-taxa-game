"""Fetch Chinese insect species that have at least one reusable photo."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT, batch_taxa, paginate

INSECTA = 47158
ALLOWED = "cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa"
RAW = ROOT / "data" / "raw"
CURATED = ROOT / "data" / "curated"
RAW.mkdir(parents=True, exist_ok=True)
CURATED.mkdir(parents=True, exist_ok=True)


def order_id(ancestry: str | None) -> int | None:
    if not ancestry:
        return None
    parts = [int(x) for x in ancestry.split("/")]
    try:
        insecta_at = parts.index(INSECTA)
    except ValueError:
        return None
    # 47158/184884/<order>...
    return parts[insecta_at + 2] if len(parts) > insecta_at + 2 else None


def main() -> None:
    print("Fetching China insect species with reusable photos ...")
    results = paginate(
        "/observations/species_counts",
        {
            "place_id": 6903,
            "taxon_id": INSECTA,
            "quality_grade": "research",
            "photo_license": ALLOWED,
            "per_page": 200,
            "locale": "zh-CN",
        },
        max_pages=100,
    )
    (RAW / "china_species_counts.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for item in results:
        taxon = item.get("taxon") or {}
        if taxon.get("rank") != "species" or not taxon.get("is_active", True):
            continue
        oid = order_id(taxon.get("ancestry"))
        rows.append(
            {
                "taxon_id": taxon["id"],
                "name": taxon["name"],
                "zh": taxon.get("preferred_common_name") or None,
                "ancestry": taxon.get("ancestry"),
                "parent_id": taxon.get("parent_id"),
                "order_id": oid,
                "count": item.get("count"),
                "observations_count": taxon.get("observations_count"),
            }
        )

    orders = batch_taxa(sorted({r["order_id"] for r in rows if r["order_id"]}))
    for row in rows:
        order = orders.get(row["order_id"]) if row["order_id"] else None
        row["order_name"] = order.get("name") if order else None
        row["order_zh"] = order.get("preferred_common_name") if order else None

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "iNaturalist observations/species_counts, China place 6903",
        "filters": {
            "quality_grade": "research",
            "photo_license": ALLOWED.split(","),
        },
        "counts": {
            "species": len(rows),
            "orders": len({r["order_id"] for r in rows if r["order_id"]}),
        },
        "species": rows,
    }
    (CURATED / "candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print("Top orders:")
    for (oid, name), count in Counter(
        (r["order_id"], f"{r['order_name']} / {r['order_zh']}") for r in rows
    ).most_common(25):
        print(f"  {oid}\t{name}\t{count}")


if __name__ == "__main__":
    main()
