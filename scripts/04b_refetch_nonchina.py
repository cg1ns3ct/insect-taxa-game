"""Refetch records whose image came from outside China, keeping already-China records."""
from __future__ import annotations

import importlib.util
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import inat_api
from inat_api import ROOT, get

inat_api.MIN_INTERVAL = 1.0

CURATED = ROOT / "data" / "curated"
SOURCE = CURATED / "target_records_global.json"
DEST = CURATED / "target_records.json"

spec = importlib.util.spec_from_file_location(
    "fetch_records", ROOT / "scripts" / "04_fetch_records.py"
)
assert spec and spec.loader
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)

CHINA_RE = re.compile(
    r"中国|香港|澳门|澳門|台湾|臺灣|China|Hong Kong|Macau|Taiwan|(?:^|,\s*)CN(?:\s*,|$)",
    re.IGNORECASE,
)


def is_china(record: dict) -> bool:
    place = record.get("place_guess") or ""
    return bool(CHINA_RE.search(place))


def fetch_china(record: dict):
    tid = int(record["taxon_id"])
    target = {
        "taxon_id": tid,
        "name": record["scientific_name"],
        "zh": record.get("zh_name"),
        "order_id": record.get("order_id"),
        "order_name": record.get("order_name"),
        "order_zh": record.get("order_zh"),
    }
    for per_page in (1, 10):
        data = get(
            "/observations",
            {
                "taxon_id": tid,
                "place_id": 6903,
                "quality_grade": "research",
                "photos": "true",
                "photo_license": fetch.ALLOWED_PARAM,
                "per_page": per_page,
                "order_by": "votes",
                "locale": "zh-CN",
            },
        )
        candidates = [o for o in data.get("results", []) if fetch.acceptable(o)]
        if candidates:
            best = max(candidates, key=fetch.obs_score)
            chosen = fetch.compact(target, best, "community")
            chosen["place_scope"] = "china"
            return chosen
    return None


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload["records"]
    keep = {k: v for k, v in records.items() if is_china(v) or v.get("source") == "owner"}
    refetch = {k: v for k, v in records.items() if k not in keep}
    print(f"keeping={len(keep)} refetching={len(refetch)}")

    updated = dict(keep)
    for record in updated.values():
        record["place_scope"] = "china"
    failed = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(fetch_china, record): key for key, record in refetch.items()}
        done = 0
        for future in as_completed(futures):
            key = futures[future]
            done += 1
            try:
                chosen = future.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR {key}: {type(exc).__name__} {exc}")
                chosen = None
            if chosen:
                updated[key] = chosen
            else:
                fallen = dict(records[key])
                fallen["place_scope"] = "global"
                updated[key] = fallen
                failed.append(key)
            if done % 25 == 0 or done == len(refetch):
                print(f"  {done}/{len(refetch)}; failed={len(failed)}", flush=True)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "targets": len(records),
            "records": len(updated),
            "china": sum(1 for r in updated.values() if r.get("place_scope") == "china"),
            "global_fallback": sum(1 for r in updated.values() if r.get("place_scope") == "global"),
            "owner_records": sum(1 for r in updated.values() if r.get("owner")),
        },
        "records": updated,
        "missing": [],
    }
    DEST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
