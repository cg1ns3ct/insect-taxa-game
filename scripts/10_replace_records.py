"""Replace five hand-picked records whose photos were unsuitable for the quiz."""
from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from inat_api import ROOT, get

CURATED = ROOT / "data" / "curated"
RECORDS = CURATED / "target_records.json"

spec = importlib.util.spec_from_file_location(
    "fetch_records", ROOT / "scripts" / "04_fetch_records.py"
)
assert spec and spec.loader
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)

# taxon_id -> (new observation id, desired photo id)
REPLACEMENTS = {
    424957: (295077526, 531682794),  # Anthomyia illocata
    146737: (88716044, 146403147),  # Velarifictorus micado
    130335: (252227358, 451477880),  # Lexias pardalis
    67598: (145042248, 249074753),  # Solenopsis invicta
    98382: (199567670, 351960881),  # Copera marginipes
    470244: (180281240, 313998636),  # Sisyra nikkoana
    491973: (149326652, 257303990),  # Neope muirheadii
    125574: (291119277, 523763435),  # Graphium cloanthus
}

CHINA_RE = re.compile(
    r"中国|香港|澳门|澳門|台湾|臺灣|China|Hong Kong|Macau|Taiwan|(?:^|,\s*)CN(?:\s*,|$)|[\u4e00-\u9fff]",
    re.IGNORECASE,
)


def main() -> None:
    payload = json.loads(RECORDS.read_text(encoding="utf-8"))
    records = payload["records"]
    changed = []
    for taxon_id, (observation_id, photo_id) in REPLACEMENTS.items():
        old = records[str(taxon_id)]
        data = get(f"/observations/{observation_id}")
        observation = data["results"][0]
        if int(observation["taxon"]["id"]) != int(taxon_id):
            raise RuntimeError(
                f"observation {observation_id} is {observation['taxon']['name']}, "
                f"expected taxon {taxon_id}"
            )
        photos = [
            p
            for p in observation.get("photos") or []
            if int(p["id"]) == int(photo_id)
        ]
        if not photos:
            raise RuntimeError(f"photo {photo_id} not found in {observation_id}")
        observation["photos"] = photos
        if not fetch.acceptable(observation):
            raise RuntimeError(f"observation {observation_id} is not acceptable")

        target = {
            "taxon_id": int(taxon_id),
            "name": old["scientific_name"],
            "zh": old.get("zh_name"),
            "order_id": old.get("order_id"),
            "order_name": old.get("order_name"),
            "order_zh": old.get("order_zh"),
        }
        new = fetch.compact(target, observation, "community")
        new["place_scope"] = (
            "china" if CHINA_RE.search(new.get("place_guess") or "") else "global"
        )
        records[str(taxon_id)] = new
        changed.append(
            {
                "taxon_id": taxon_id,
                "name": old["scientific_name"],
                "old_observation": old["observation_id"],
                "new_observation": observation_id,
                "new_photo": photo_id,
                "place": new.get("place_guess"),
                "license": new.get("photo_license"),
            }
        )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "targets": payload["counts"]["targets"],
            "records": len(records),
            "replaced": len(changed),
            "owner_records": sum(1 for r in records.values() if r.get("owner")),
        },
        "records": records,
        "missing": payload.get("missing", []),
        "replaced": changed,
    }
    RECORDS.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(changed, ensure_ascii=False, indent=2))
    print(json.dumps(out["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
