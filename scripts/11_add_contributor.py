"""Add yy_never_air_force's research-grade insect records.

Policy:
- species already represented by cg1ns3ct's own record keep the owner record;
- species currently represented by a community record are upgraded to yy's record;
- species not yet in the pool are added as new target species.
"""
from __future__ import annotations

import importlib.util
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT, batch_taxa, paginate

CURATED = ROOT / "data" / "curated"
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
CONTRIBUTOR_ID = 10593542
CONTRIBUTOR_LOGIN = "yy_never_air_force"

spec = importlib.util.spec_from_file_location(
    "fetch_records", ROOT / "scripts" / "04_fetch_records.py"
)
assert spec and spec.loader
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


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
    observations = paginate(
        "/observations",
        {
            "user_id": CONTRIBUTOR_ID,
            "taxon_id": 47158,
            "quality_grade": "research",
            "photos": "true",
            "per_page": 200,
            "locale": "zh-CN",
        },
    )
    (RAW / "yy_observations.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_species: dict[int, list[dict]] = defaultdict(list)
    for observation in observations:
        taxon = observation.get("taxon") or {}
        if taxon.get("rank") != "species":
            continue
        if not fetch.acceptable(observation):
            continue
        by_species[int(taxon["id"])].append(observation)

    targets_payload = json.loads((CURATED / "targets.json").read_text(encoding="utf-8"))
    records_payload = json.loads(
        (CURATED / "target_records.json").read_text(encoding="utf-8")
    )
    targets = {int(row["taxon_id"]): row for row in targets_payload["species"]}
    records = {int(key): value for key, value in records_payload["records"].items()}
    candidates = {
        int(row["taxon_id"]): row
        for row in json.loads(
            (CURATED / "candidates.json").read_text(encoding="utf-8")
        )["species"]
    }

    new_ids = [tid for tid in by_species if tid not in targets]
    taxa = batch_taxa(new_ids) if new_ids else {}

    added_targets = []
    replaced = []
    kept_owner = []
    for taxon_id, obs_list in by_species.items():
        obs_list.sort(key=fetch.obs_score, reverse=True)
        observation = obs_list[0]
        taxon = observation["taxon"]

        target = targets.get(taxon_id)
        if target is None:
            candidate = candidates.get(taxon_id)
            taxon_zh = taxa.get(taxon_id, {}).get("preferred_common_name")
            target = {
                "taxon_id": taxon_id,
                "name": taxon["name"],
                "zh": (candidate or {}).get("zh") or taxon_zh,
                "ancestry": taxon.get("ancestry"),
                "parent_id": taxon.get("parent_id"),
                "order_id": order_id(taxon.get("ancestry")),
                "order_name": (candidate or {}).get("order_name"),
                "order_zh": (candidate or {}).get("order_zh"),
                "count": len(obs_list),
                "owner": False,
                "reason": "contributor",
                "contributor": CONTRIBUTOR_LOGIN,
            }
            targets[taxon_id] = target
            added_targets.append(taxon_id)

        record = fetch.compact(target, observation, "contributor")
        record["source"] = "contributor"
        record["owner"] = False
        record["contributor"] = CONTRIBUTOR_LOGIN
        record["place_scope"] = "china"

        current = records.get(taxon_id)
        if current is None or current.get("source") == "community":
            if current is not None:
                replaced.append(taxon_id)
            records[taxon_id] = record
        else:
            kept_owner.append(taxon_id)

    targets_out = {
        **targets_payload,
        "counts": {
            **targets_payload.get("counts", {}),
            "total": len(targets),
            "contributor": sum(1 for t in targets.values() if t.get("contributor")),
        },
        "species": sorted(targets.values(), key=lambda row: row["taxon_id"]),
    }
    (CURATED / "targets.json").write_text(
        json.dumps(targets_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    records_out = {
        **records_payload,
        "counts": {
            **records_payload.get("counts", {}),
            "targets": len(targets),
            "records": len(records),
            "contributor_records": sum(
                1 for r in records.values() if r.get("source") == "contributor"
            ),
        },
        "records": {str(k): records[k] for k in sorted(records)},
    }
    (CURATED / "target_records.json").write_text(
        json.dumps(records_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contributor": CONTRIBUTOR_LOGIN,
        "observations": len(observations),
        "species": len(by_species),
        "added_targets": len(added_targets),
        "replaced_community": len(replaced),
        "kept_owner": len(kept_owner),
        "new_species": [
            {
                "taxon_id": tid,
                "name": by_species[tid][0]["taxon"]["name"],
                "zh": by_species[tid][0]["taxon"].get("preferred_common_name"),
            }
            for tid in added_targets
        ],
    }
    (CURATED / "contributor_integration.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
