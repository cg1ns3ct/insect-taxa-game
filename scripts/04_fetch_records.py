"""Pick one observation/photo per target species.

The owner's own records are preferred when available. Community records must be
research grade and carry a reusable photo license. Derivative evidence (eggs,
galls, mines, etc.) is tagged and kept out of the default round pool later.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT, get

CURATED = ROOT / "data" / "curated"
ALLOWED = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
ALLOWED_PARAM = ",".join(sorted(ALLOWED))
LIFE_STAGE = {
    2: "adult",
    3: "teneral",
    4: "pupa",
    5: "nymph",
    6: "larva",
    7: "egg",
    8: "juvenile",
    16: "subimago",
}
EVIDENCE = {
    23: "feather",
    24: "organism",
    25: "scat",
    26: "track",
    27: "bone",
    28: "molt",
    29: "gall",
    30: "egg",
    31: "hair",
    32: "leafmine",
    35: "construction",
}
ALIVE = {18: "alive", 19: "dead", 20: "unknown"}


def photo_area(photo: dict) -> int:
    dims = photo.get("original_dimensions") or {}
    return int(dims.get("width") or 0) * int(dims.get("height") or 0)


def best_photo(observation: dict) -> dict | None:
    photos = [
        p
        for p in observation.get("photos") or []
        if p.get("license_code") in ALLOWED and p.get("url")
    ]
    return max(photos, key=photo_area) if photos else None


def annotations(observation: dict) -> dict:
    values = {}
    for annotation in observation.get("annotations") or []:
        attr = annotation.get("controlled_attribute_id")
        if attr in (1, 17, 22):
            values[attr] = annotation.get("controlled_value_id")
    return {
        "life_stage": LIFE_STAGE.get(values.get(1)),
        "alive": ALIVE.get(values.get(17)),
        "evidence": EVIDENCE.get(values.get(22)),
    }


def obs_score(observation: dict) -> float:
    score = 10 * int(observation.get("num_identification_agreements") or 0)
    score += 2 * int(observation.get("identifications_count") or 0)
    score += 3 if observation.get("quality_grade") == "research" else 0
    score += 2 * len(observation.get("photos") or [])
    photo = best_photo(observation)
    if photo:
        score += photo_area(photo) / 1_000_000
    if not observation.get("captive"):
        score += 2
    ann = annotations(observation)
    if ann["evidence"] == "organism":
        score += 10
    elif ann["evidence"] is None:
        score += 4
    else:
        score -= 20
    if ann["life_stage"] == "adult":
        score += 6
    elif ann["life_stage"] in {"nymph", "larva"}:
        score += 3
    elif ann["life_stage"] in {"egg", "pupa"}:
        score -= 20
    return score


def acceptable(observation: dict) -> bool:
    if not observation.get("photos"):
        return False
    if not best_photo(observation):
        return False
    if not observation.get("place_guess"):
        return False
    if observation.get("geoprivacy") == "private":
        return False
    if observation.get("captive"):
        return False
    return True


def compact(taxon: dict, observation: dict, source: str) -> dict:
    photo = best_photo(observation)
    annotation = annotations(observation)
    return {
        "taxon_id": int(taxon["taxon_id"]),
        "scientific_name": taxon["name"],
        "zh_name": taxon.get("zh"),
        "order_id": taxon.get("order_id"),
        "order_name": taxon.get("order_name"),
        "order_zh": taxon.get("order_zh"),
        "owner": source == "owner",
        "source": source,
        "observation_id": observation["id"],
        "observation_url": observation.get("uri")
        or f"https://www.inaturalist.org/observations/{observation['id']}",
        "quality_grade": observation.get("quality_grade"),
        "observed_on": observation.get("observed_on"),
        "place_guess": observation.get("place_guess"),
        "latitude": (observation.get("location") or "").split(",")[0] or None,
        "longitude": (observation.get("location") or "").split(",")[-1] or None,
        "geoprivacy": observation.get("geoprivacy"),
        "obscured": observation.get("obscured"),
        "num_identification_agreements": observation.get("num_identification_agreements"),
        "identifications_count": observation.get("identifications_count"),
        "photo_id": photo.get("id"),
        "photo_license": photo.get("license_code"),
        "photo_attribution": photo.get("attribution"),
        "photo_url_square": photo.get("url"),
        "photo_url_large": (photo.get("url") or "").replace("/square.", "/large."),
        "photo_width": (photo.get("original_dimensions") or {}).get("width"),
        "photo_height": (photo.get("original_dimensions") or {}).get("height"),
        "annotations": annotation,
    }


def owner_observation(candidate: dict) -> dict | None:
    photo = candidate.get("photo")
    if not photo or not candidate.get("place_guess"):
        return None
    observation = {
        "id": candidate["observation_id"],
        "uri": candidate.get("observation_url"),
        "quality_grade": candidate.get("quality_grade"),
        "observed_on": candidate.get("observed_on"),
        "place_guess": candidate.get("place_guess"),
        "geoprivacy": candidate.get("geoprivacy"),
        "obscured": candidate.get("obscured"),
        "captive": candidate.get("captive"),
        "location": None,
        "num_identification_agreements": candidate.get("num_identification_agreements"),
        "identifications_count": candidate.get("identifications_count"),
        "photos": [
            {
                "id": photo["photo_id"],
                "license_code": photo["license_code"],
                "url": photo["url_square"],
                "attribution": photo["attribution"],
                "original_dimensions": {
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                },
            }
        ],
    }
    return observation if acceptable(observation) else None


def fetch_record(target: dict, owner_species: dict | None) -> tuple[int, dict | None]:
    tid = int(target["taxon_id"])
    if owner_species:
        observation = owner_observation(owner_species["chosen"])
        if observation:
            chosen = compact(target, observation, "owner")
            chosen["annotations"] = owner_species["chosen"].get("annotations") or {}
            chosen["place_scope"] = "china"
            return tid, chosen

    data = get(
        "/observations",
        {
            "taxon_id": tid,
            "place_id": 6903,
            "quality_grade": "research",
            "photos": "true",
            "photo_license": ALLOWED_PARAM,
            "per_page": 1,
            "order_by": "votes",
            "locale": "zh-CN",
        },
    )
    candidates = [o for o in data.get("results", []) if acceptable(o)]
    if not candidates:
        data = get(
            "/observations",
            {
                "taxon_id": tid,
                "place_id": 6903,
                "quality_grade": "research",
                "photos": "true",
                "photo_license": ALLOWED_PARAM,
                "per_page": 10,
                "locale": "zh-CN",
            },
        )
        candidates = [o for o in data.get("results", []) if acceptable(o)]
    place_scope = "china"
    if not candidates:
        # A small number of target species may only have reusable photos from
        # outside China. Keep them, but label the source scope honestly.
        data = get(
            "/observations",
            {
                "taxon_id": tid,
                "quality_grade": "research",
                "photos": "true",
                "photo_license": ALLOWED_PARAM,
                "per_page": 20,
                "locale": "zh-CN",
            },
        )
        candidates = [o for o in data.get("results", []) if acceptable(o)]
        place_scope = "global"
    if not candidates:
        return tid, None
    best = max(candidates, key=obs_score)
    chosen = compact(target, best, "community")
    chosen["place_scope"] = place_scope
    return tid, chosen


def main() -> None:
    targets = json.loads((CURATED / "targets.json").read_text(encoding="utf-8"))
    owner = json.loads((CURATED / "user_species.json").read_text(encoding="utf-8"))
    owner_by_id = {int(s["taxon_id"]): s for s in owner["species"]}
    rows = targets["species"]

    records: dict[int, dict] = {}
    missing: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(fetch_record, target, owner_by_id.get(int(target["taxon_id"]))): target
            for target in rows
        }
        done = 0
        for future in as_completed(futures):
            target = futures[future]
            done += 1
            try:
                tid, record = future.result()
            except Exception as exc:  # noqa: BLE001 - keep the pipeline alive
                print(f"  ERROR {target['name']}: {type(exc).__name__} {exc}")
                missing.append(target)
                continue
            if record:
                records[tid] = record
            else:
                missing.append(target)
            if done % 25 == 0 or done == len(rows):
                print(f"  {done}/{len(rows)}; records={len(records)}; missing={len(missing)}")

    # Keep target order deterministic.
    ordered = {
        str(int(t["taxon_id"])): records[int(t["taxon_id"])]
        for t in rows
        if int(t["taxon_id"]) in records
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "targets": len(rows),
            "records": len(ordered),
            "owner_records": sum(1 for r in ordered.values() if r["owner"]),
            "missing": len(missing),
        },
        "records": ordered,
        "missing": missing,
    }
    (CURATED / "target_records.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print("Wrote data/curated/target_records.json")


if __name__ == "__main__":
    main()
