"""Build the public taxonomy tree and round data from curated records."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT, batch_taxa, descendants

CURATED = ROOT / "data" / "curated"
PUBLIC = ROOT / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

INSECTA = 47158
SCORING = {
    "order": 10,
    "suborder": 20,
    "family": 40,
    "subfamily": 55,
    "genus": 75,
    "species": 100,
}
SCORING_RANKS = set(SCORING)
CHINA_RE = re.compile(
    r"中国|香港|澳门|澳門|台湾|臺灣|China|Hong Kong|Macau|Taiwan|(?:^|,\s*)CN(?:\s*,|$)",
    re.IGNORECASE,
)


def infer_scope(record: dict) -> str:
    if record.get("place_scope"):
        return record["place_scope"]
    return "china" if CHINA_RE.search(record.get("place_guess") or "") else "global"


def add_taxa(store: dict[int, dict], rows: list[dict]) -> None:
    for taxon in rows:
        store[int(taxon["id"])] = taxon


def main() -> None:
    targets_payload = json.loads((CURATED / "targets.json").read_text(encoding="utf-8"))
    candidates_payload = json.loads(
        (CURATED / "candidates.json").read_text(encoding="utf-8")
    )
    records_payload = json.loads(
        (CURATED / "target_records.json").read_text(encoding="utf-8")
    )
    target_rows = targets_payload["species"]
    records = {int(k): v for k, v in records_payload["records"].items()}
    target_ids = [int(t["taxon_id"]) for t in target_rows]

    taxa: dict[int, dict] = {}
    print("Fetching target taxa ...")
    add_taxa(taxa, batch_taxa(target_ids).values())

    ancestor_ids: set[int] = set()
    for taxon in list(taxa.values()):
        ancestor_ids.update(int(i) for i in taxon.get("ancestor_ids") or [])
    print(f"Fetching {len(ancestor_ids)} target ancestors ...")
    add_taxa(taxa, batch_taxa(sorted(ancestor_ids - set(taxa))).values())

    # Which orders/families/genera actually contain targets?
    target_orders: set[int] = set()
    target_families: set[int] = set()
    target_genera: set[int] = set()
    for tid in target_ids:
        taxon = taxa.get(tid)
        if not taxon:
            continue
        for aid in [*taxon.get("ancestor_ids", []), tid]:
            ancestor = taxa.get(int(aid))
            if not ancestor:
                continue
            rank = ancestor.get("rank")
            if rank == "order":
                target_orders.add(int(aid))
            elif rank == "family":
                target_families.add(int(aid))
            elif rank == "genus":
                target_genera.add(int(aid))

    print(f"Targets: {len(target_ids)} species, {len(target_orders)} orders, "
          f"{len(target_families)} families, {len(target_genera)} genera")

    # All insect orders, for wrong-order choices.
    print("Fetching insect orders ...")
    add_taxa(taxa, descendants(INSECTA, "order", per_page=200, max_pages=2))

    # Every family in each target order, for wrong-family choices.
    all_family_ids: set[int] = set()
    for oid in sorted(target_orders):
        rows = descendants(oid, "family", per_page=200, max_pages=5)
        add_taxa(taxa, rows)
        all_family_ids.update(int(r["id"]) for r in rows)

    # Subfamilies and common genera only inside target families. Non-target
    # families stay as selectable leaves, which is enough for a wrong family.
    for fid in sorted(target_families):
        subs = descendants(fid, "subfamily", per_page=200, max_pages=2)
        add_taxa(taxa, subs)
        genera = descendants(
            fid,
            "genus",
            per_page=30,
            order_by="observations_count",
            max_pages=1,
        )
        add_taxa(taxa, genera)

    # Common congeners make species-level wrong answers possible. Reuse the
    # candidate table instead of making one API call per genus.
    print("Adding congeners for species-level distractors ...")
    by_genus: dict[int, list[dict]] = {}
    for row in candidates_payload["species"]:
        if int(row["taxon_id"]) in target_ids:
            continue
        ancestry = {int(i) for i in (row.get("ancestry") or "").split("/") if i}
        for gid in target_genera & ancestry:
            by_genus.setdefault(gid, []).append(row)
    for gid, rows in by_genus.items():
        rows.sort(key=lambda r: -(r.get("count") or 0))
        for row in rows[:3]:
            add_taxa(
                taxa,
                [
                    {
                        "id": int(row["taxon_id"]),
                        "name": row["name"],
                        "preferred_common_name": row.get("zh"),
                        "rank": "species",
                        "rank_level": 10,
                        "parent_id": row.get("parent_id"),
                        "ancestor_ids": [
                            int(i) for i in (row.get("ancestry") or "").split("/") if i
                        ],
                        "observations_count": row.get("count"),
                    }
                ],
            )

    # Close the tree over all ancestors of every selected node.
    print(f"Closing tree over {len(taxa)} taxa ...")
    for _ in range(3):
        missing: set[int] = set()
        for taxon in taxa.values():
            for aid in taxon.get("ancestor_ids") or []:
                aid = int(aid)
                if aid not in taxa:
                    missing.add(aid)
        if not missing:
            break
        print(f"  fetching {len(missing)} missing ancestors")
        add_taxa(taxa, batch_taxa(sorted(missing)).values())

    # Keep only the insect subtree.
    nodes: dict[int, dict] = {}
    for tid, taxon in taxa.items():
        ancestry = [int(i) for i in taxon.get("ancestor_ids") or []]
        if tid != INSECTA and INSECTA not in ancestry:
            continue
        parent_id = taxon.get("parent_id")
        nodes[tid] = {
            "id": tid,
            "parentId": int(parent_id) if parent_id else None,
            "name": taxon.get("name"),
            "zh": taxon.get("preferred_common_name"),
            "rank": taxon.get("rank"),
            "rankLevel": taxon.get("rank_level"),
            "observationsCount": taxon.get("observations_count"),
            "scoring": taxon.get("rank") in SCORING_RANKS,
            "children": [],
        }

    # Drop nodes whose parent is outside the insect subtree (should be only the root).
    for tid, node in nodes.items():
        parent_id = node["parentId"]
        if parent_id in nodes and parent_id != tid:
            nodes[parent_id]["children"].append(tid)

    # Order children by rank level then observation count then name.
    def child_key(tid: int):
        node = nodes[tid]
        return (-(node["rankLevel"] or 0), -(node["observationsCount"] or 0), node["name"])

    for node in nodes.values():
        node["children"].sort(key=child_key)

    # Attach target paths and round records. Derivative evidence (egg cases,
    # galls, mines, etc.) is kept as an extra pool, not in the default game.
    rounds = []
    extras = []
    for target in target_rows:
        tid = int(target["taxon_id"])
        record = records.get(tid)
        if not record or tid not in nodes:
            continue
        annotations = record.get("annotations") or {}
        evidence = annotations.get("evidence")
        life_stage = annotations.get("life_stage")
        derivative = evidence not in (None, "organism") or life_stage in {"egg", "pupa"}
        item = {
            "taxonId": tid,
            "image": f"images/{record['photo_id']}.webp",
            "source": record["source"],
            "placeScope": infer_scope(record),
            "observationId": record["observation_id"],
            "observationUrl": record["observation_url"],
            "observedOn": record.get("observed_on"),
            "placeGuess": record.get("place_guess"),
            "license": record.get("photo_license"),
            "attribution": record.get("photo_attribution"),
            "agreements": record.get("num_identification_agreements"),
            "identifications": record.get("identifications_count"),
            "evidence": evidence,
            "lifeStage": life_stage,
        }
        if derivative:
            extras.append(item)
        else:
            rounds.append(item)
    rounds.sort(key=lambda r: (nodes[r["taxonId"]]["rankLevel"] or 0, r["taxonId"]))
    extras.sort(key=lambda r: (nodes[r["taxonId"]]["rankLevel"] or 0, r["taxonId"]))

    payload = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "rootId": INSECTA,
        "scoring": SCORING,
        "scoringRanks": list(SCORING),
        "counts": {
            "taxa": len(nodes),
            "rounds": len(rounds),
            "targets": len(target_rows),
            "ownerRounds": sum(1 for r in rounds if r["source"] == "owner"),
            "extras": len(extras),
        },
        "nodes": {str(k): v for k, v in nodes.items()},
        "rounds": rounds,
        "extras": extras,
    }
    (PUBLIC / "game.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print(f"Wrote {PUBLIC / 'game.json'}")


if __name__ == "__main__":
    main()
