"""Choose the first target pool from the owner's records plus common China species."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT

CURATED = ROOT / "data" / "curated"

# Broad taxonomic quotas. They sum to a little over 750 because the owner's
# species are inserted first and some orders will run out of good candidates.
QUOTAS = {
    "Lepidoptera": 170,
    "Coleoptera": 160,
    "Hemiptera": 100,
    "Hymenoptera": 100,
    "Diptera": 80,
    "Orthoptera": 45,
    "Odonata": 40,
    "Mantodea": 20,
    "Dermaptera": 8,
    "Blattodea": 8,
    "Phasmida": 8,
    "Megaloptera": 5,
    "Neuroptera": 5,
    "Mecoptera": 3,
    "Ephemeroptera": 3,
    "Trichoptera": 3,
    "Psocodea": 2,
}
MAX_PER_GENUS = 3
MAX_PER_ORDER = 190


def order_id(ancestry: str | None) -> int | None:
    if not ancestry:
        return None
    parts = [int(x) for x in ancestry.split("/")]
    try:
        at = parts.index(47158)
    except ValueError:
        return None
    return parts[at + 2] if len(parts) > at + 2 else None


def main() -> None:
    candidates = json.loads((CURATED / "candidates.json").read_text(encoding="utf-8"))
    user = json.loads((CURATED / "user_species.json").read_text(encoding="utf-8"))

    by_id = {int(s["taxon_id"]): dict(s) for s in candidates["species"]}
    selected: dict[int, dict] = {}

    # 1. Owner's species always enter first.
    for item in user["species"]:
        tid = int(item["taxon_id"])
        base = by_id.get(tid, {})
        row = {
            **base,
            "taxon_id": tid,
            "name": item["name"],
            "zh": base.get("zh") or item.get("zh"),
            "ancestry": base.get("ancestry") or item.get("ancestry"),
            "order_id": base.get("order_id") or order_id(item.get("ancestry")),
            "order_name": base.get("order_name"),
            "order_zh": base.get("order_zh"),
            "parent_id": base.get("parent_id"),
            "count": base.get("count", item.get("observation_count", 0)),
            "owner": True,
            "owner_observations": item.get("observation_count", 0),
            "reason": "owner",
        }
        selected[tid] = row

    # 2. Fill order quotas with common, diverse species.
    by_order: dict[str, list[dict]] = defaultdict(list)
    for row in by_id.values():
        if row.get("order_name"):
            by_order[row["order_name"]].append(row)

    for order_name, rows in by_order.items():
        rows.sort(key=lambda r: (r.get("zh") is None, -(r.get("count") or 0), r["name"]))
        quota = QUOTAS.get(order_name, 3)
        current = sum(1 for r in selected.values() if r.get("order_name") == order_name)
        per_genus: Counter = Counter(
            r.get("parent_id") for r in selected.values() if r.get("order_name") == order_name
        )
        # First pass: respect genus cap and prefer species with Chinese names.
        for row in rows:
            if current >= quota or len(selected) >= 800:
                break
            if row["taxon_id"] in selected:
                continue
            if not row.get("zh"):
                continue
            if per_genus[row.get("parent_id")] >= MAX_PER_GENUS:
                continue
            selected[row["taxon_id"]] = {**row, "owner": False, "reason": "quota"}
            per_genus[row.get("parent_id")] += 1
            current += 1

        # Second pass: relax the genus cap if the order still has room.
        for row in rows:
            if current >= quota or len(selected) >= 800:
                break
            if row["taxon_id"] in selected or not row.get("zh"):
                continue
            selected[row["taxon_id"]] = {**row, "owner": False, "reason": "quota-relaxed"}
            current += 1

    # 3. If the global count is still short, fill from remaining species with zh.
    if len(selected) < 700:
        rest = [
            row
            for row in by_id.values()
            if row["taxon_id"] not in selected and row.get("zh")
        ]
        rest.sort(key=lambda r: -(r.get("count") or 0))
        for row in rest:
            if len(selected) >= 750:
                break
            selected[row["taxon_id"]] = {**row, "owner": False, "reason": "fill"}

    rows = sorted(
        selected.values(),
        key=lambda r: (r.get("order_name") or "zzz", -(r.get("count") or 0), r["name"]),
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "total": len(rows),
            "owner": sum(1 for r in rows if r.get("owner")),
            "with_zh": sum(1 for r in rows if r.get("zh")),
            "orders": len({r.get("order_id") for r in rows if r.get("order_id")}),
        },
        "quotas": QUOTAS,
        "species": rows,
    }
    (CURATED / "targets.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print("By order:")
    for name, count in Counter(r.get("order_name") for r in rows).most_common():
        print(f"  {name or '?'}\t{count}")
    print("Wrote data/curated/targets.json")


if __name__ == "__main__":
    main()
