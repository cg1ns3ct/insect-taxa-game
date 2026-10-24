"""Human-readable audit of the generated game data."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "public" / "data" / "game.json"
IMAGES = ROOT / "public" / "images"


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
    extras = data.get("extras", [])
    print("counts", data["counts"])
    print("rounds", len(rounds), "extras", len(extras))
    print("owner rounds", sum(1 for r in rounds if r["source"] == "owner"))
    print("licenses", Counter(r.get("license") for r in rounds))

    ranks = Counter()
    missing_zh = []
    path_lengths = Counter()
    order_counts = Counter()
    family_counts = Counter()
    for round_ in rounds:
        tid = round_["taxonId"]
        path = path_of(tid, nodes)
        path_lengths[len(path)] += 1
        for node in path:
            ranks[node["rank"]] += 1
            if node["rank"] == "order":
                order_counts[node["zh"] or node["name"]] += 1
            if node["rank"] == "family":
                family_counts[node["zh"] or node["name"]] += 1
        target = nodes.get(str(tid))
        if not target or not target.get("zh"):
            missing_zh.append((tid, target.get("name") if target else None))

    print("path lengths", dict(sorted(path_lengths.items())))
    print("rank coverage", dict(ranks))
    print("orders in rounds", len(order_counts))
    print("top orders", order_counts.most_common(12))
    print("families", len(family_counts))
    print("missing zh", len(missing_zh), missing_zh[:10])
    sizes = [p.stat().st_size for p in IMAGES.glob("*.webp")]
    print("images", len(sizes), "MB", round(sum(sizes) / 1_000_000, 1))
    if sizes:
        print("avg KB", round(sum(sizes) / len(sizes) / 1000, 1), "min KB", round(min(sizes) / 1000, 1))


if __name__ == "__main__":
    main()
