"""Fetch the owner's public iNaturalist insect records and pick one record per species."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT, paginate

USER_ID = 4887934
USER_LOGIN = "cg1ns3ct"
INSECTA = 47158
ALLOWED = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}

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
SEX = {10: "female", 11: "male", 20: "unknown"}

RAW = ROOT / "data" / "raw"
CURATED = ROOT / "data" / "curated"
RAW.mkdir(parents=True, exist_ok=True)
CURATED.mkdir(parents=True, exist_ok=True)


def photo_area(photo: dict) -> int:
    dims = photo.get("original_dimensions") or {}
    return int(dims.get("width") or 0) * int(dims.get("height") or 0)


def best_photo(observation: dict) -> dict | None:
    candidates = [
        p
        for p in observation.get("photos", [])
        if p.get("license_code") in ALLOWED and p.get("url")
    ]
    if not candidates:
        return None
    return max(candidates, key=photo_area)


def annotation_values(observation: dict) -> dict:
    values = {}
    for annotation in observation.get("annotations") or []:
        attr = annotation.get("controlled_attribute_id")
        value = annotation.get("controlled_value_id")
        if attr in (1, 9, 17, 22):
            values[attr] = value
    return {
        "life_stage": LIFE_STAGE.get(values.get(1)),
        "sex": SEX.get(values.get(9)),
        "alive": ALIVE.get(values.get(17)),
        "evidence": EVIDENCE.get(values.get(22)),
        "raw": values,
    }


def observation_score(observation: dict) -> float:
    score = 0.0
    score += 10 * int(observation.get("num_identification_agreements") or 0)
    score += 2 * int(observation.get("identifications_count") or 0)
    if observation.get("quality_grade") == "research":
        score += 5
    score += 2 * len(observation.get("photos") or [])
    photo = best_photo(observation)
    if photo:
        score += photo_area(photo) / 1_000_000
    if not observation.get("captive"):
        score += 2

    annotations = annotation_values(observation)
    if annotations["evidence"] == "organism":
        score += 10
    elif annotations["evidence"] is None:
        score += 4
    else:
        # Egg cases, galls, mines etc. are legitimate records but should not
        # beat a normal organism photo when both exist.
        score -= 20
    if annotations["life_stage"] == "adult":
        score += 6
    elif annotations["life_stage"] in {"nymph", "larva"}:
        score += 3
    elif annotations["life_stage"] in {"egg", "pupa"}:
        score -= 20
    if annotations["alive"] == "alive":
        score += 2
    return score


def compact(observation: dict) -> dict:
    photo = best_photo(observation)
    taxon = observation.get("taxon") or {}
    annotations = annotation_values(observation)
    return {
        "observation_id": observation["id"],
        "observation_url": observation.get("uri"),
        "taxon_id": taxon.get("id"),
        "taxon_name": taxon.get("name"),
        "taxon_rank": taxon.get("rank"),
        "taxon_zh": taxon.get("preferred_common_name"),
        "taxon_ancestry": taxon.get("ancestry"),
        "quality_grade": observation.get("quality_grade"),
        "observed_on": observation.get("observed_on"),
        "place_guess": observation.get("place_guess"),
        "latitude": observation.get("location") and observation["location"].split(",")[0],
        "longitude": observation.get("location") and observation["location"].split(",")[1],
        "geoprivacy": observation.get("geoprivacy"),
        "obscured": observation.get("obscured"),
        "captive": observation.get("captive"),
        "license_code": observation.get("license_code"),
        "num_identification_agreements": observation.get("num_identification_agreements"),
        "identifications_count": observation.get("identifications_count"),
        "description": observation.get("description"),
        "tags": observation.get("tags") or [],
        "annotations": annotations,
        "photo": None
        if not photo
        else {
            "photo_id": photo.get("id"),
            "license_code": photo.get("license_code"),
            "attribution": photo.get("attribution"),
            "url_square": photo.get("url"),
            "url_large": (photo.get("url") or "").replace("/square.", "/large."),
            "width": (photo.get("original_dimensions") or {}).get("width"),
            "height": (photo.get("original_dimensions") or {}).get("height"),
        },
    }


def main() -> None:
    print("Fetching owner's insect observations ...")
    observations = paginate(
        "/observations",
        {
            "user_id": USER_ID,
            "taxon_id": INSECTA,
            "per_page": 200,
            "order_by": "observed_on",
            "order": "desc",
            "locale": "zh-CN",
        },
    )
    (RAW / "user_insect_observations.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_species: dict[int, list[dict]] = {}
    skipped = {"not_species": 0, "no_photo": 0, "no_location": 0, "captive": 0}
    for observation in observations:
        taxon = observation.get("taxon") or {}
        if taxon.get("rank") != "species" or not taxon.get("is_active", True):
            skipped["not_species"] += 1
            continue
        if not observation.get("photos"):
            skipped["no_photo"] += 1
            continue
        if not observation.get("place_guess") or observation.get("geoprivacy") == "private":
            skipped["no_location"] += 1
            continue
        if observation.get("captive"):
            skipped["captive"] += 1
            continue
        if not best_photo(observation):
            skipped["no_photo"] += 1
            continue
        by_species.setdefault(int(taxon["id"]), []).append(observation)

    species = []
    for taxon_id, obs_list in by_species.items():
        def sort_key(observation: dict):
            annotations = annotation_values(observation)
            derivative = annotations["evidence"] not in (None, "organism") or (
                annotations["life_stage"] in {"egg", "pupa"}
            )
            return (0 if derivative else 1, observation_score(observation))

        obs_list.sort(key=sort_key, reverse=True)
        chosen = obs_list[0]
        taxon = chosen["taxon"]
        species.append(
            {
                "taxon_id": taxon_id,
                "name": taxon["name"],
                "zh": taxon.get("preferred_common_name"),
                "ancestry": taxon.get("ancestry"),
                "observation_count": len(obs_list),
                "research_count": sum(
                    1 for o in obs_list if o.get("quality_grade") == "research"
                ),
                "max_agreements": max(
                    int(o.get("num_identification_agreements") or 0) for o in obs_list
                ),
                "chosen": compact(chosen),
                "observations": [compact(o) for o in obs_list],
            }
        )

    species.sort(key=lambda x: (-x["research_count"], -x["max_agreements"], x["name"]))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": {"id": USER_ID, "login": USER_LOGIN},
        "counts": {
            "observations": len(observations),
            "species": len(species),
            "skipped": skipped,
        },
        "species": species,
    }
    (CURATED / "user_species.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print("Wrote data/curated/user_species.json")


if __name__ == "__main__":
    main()
