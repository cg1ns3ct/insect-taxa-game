"""Sanity-check the generated game data before publishing."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "public" / "data" / "game.json"
IMAGES = ROOT / "public" / "images"
ALLOWED = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"}
SCORING = {"order": 15, "suborder": 25, "family": 50, "subfamily": 65, "genus": 80, "species": 100}


def path_of(tid: int, nodes: dict) -> list[dict]:
    path = []
    seen = set()
    current = nodes.get(str(tid))
    while current and current["id"] not in seen:
        path.append(current)
        seen.add(current["id"])
        parent = current.get("parentId")
        current = nodes.get(str(parent)) if parent else None
    return list(reversed(path))


def main() -> None:
    data = json.loads(GAME.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    rounds = data["rounds"]
    problems = []
    print(f"nodes={len(nodes)} rounds={len(rounds)} extras={len(data.get('extras', []))}")

    if not rounds:
        problems.append("no rounds")
    if len({r['taxonId'] for r in rounds}) != len(rounds):
        problems.append("duplicate target taxon in rounds")
    if len({r['image'] for r in rounds}) != len(rounds):
        problems.append("duplicate image in rounds")

    rank_counts = Counter()
    missing_files = 0
    for round_ in rounds:
        tid = round_["taxonId"]
        if str(tid) not in nodes:
            problems.append(f"taxon {tid} missing from nodes")
            continue
        path = path_of(tid, nodes)
        if not path or path[0]["id"] != data["rootId"]:
            problems.append(f"taxon {tid} does not reach root")
        ranks = {n["rank"] for n in path}
        if "order" not in ranks:
            problems.append(f"taxon {tid} has no order")
        for rank in ranks:
            if rank in SCORING:
                rank_counts[rank] += 1
        image_path = IMAGES / Path(round_["image"]).name
        if not image_path.exists() or image_path.stat().st_size == 0:
            missing_files += 1
        if round_.get("license") not in ALLOWED:
            problems.append(f"taxon {tid} bad license {round_.get('license')}")
        if not round_.get("attribution"):
            problems.append(f"taxon {tid} missing attribution")
        ann = round_.get("evidence")
        if ann not in (None, "organism") or round_.get("lifeStage") in {"egg", "pupa"}:
            problems.append(f"taxon {tid} derivative evidence in main rounds")

    print("ranks represented:", dict(rank_counts))
    print("missing image files:", missing_files)
    if problems:
        print("PROBLEMS:")
        for problem in problems[:30]:
            print(" -", problem)
        print(f"total problems: {len(problems)}")
        raise SystemExit(1)
    print("OK")


if __name__ == "__main__":
    main()
