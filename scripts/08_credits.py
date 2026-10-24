"""Generate a human-readable image attribution file."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDS = ROOT / "data" / "curated" / "target_records.json"
OUT = ROOT / "CREDITS.md"


def main() -> None:
    payload = json.loads(RECORDS.read_text(encoding="utf-8"))
    records = sorted(
        payload["records"].values(),
        key=lambda r: (r.get("order_name") or "", r["scientific_name"]),
    )
    lines = [
        "# 图片与记录来源",
        "",
        "本题库的图片来自 [iNaturalist](https://www.inaturalist.org/)，",
        "每张图保留原作者、许可和原观察记录链接。",
        "本项目为非商业学习项目；图片许可以下逐条列出。",
        "",
        f"- 记录数：{len(records)}",
        f"- 自有记录：{sum(1 for r in records if r.get('owner'))}",
        "- 仅使用 CC0 / CC BY / CC BY-SA / CC BY-NC / CC BY-NC-SA",
        "",
        "| 物种 | 中文名 | 记录 | 作者/许可 |",
        "|---|---|---|---|",
    ]
    for record in records:
        name = record.get("scientific_name") or ""
        zh = record.get("zh_name") or ""
        attribution = (record.get("photo_attribution") or "").replace("|", "\\|")
        lines.append(
            f"| *{name}* | {zh} | "
            f"[{record.get('observation_id')}]({record.get('observation_url')}) | "
            f"{attribution} |"
        )
    lines.extend(
        [
            "",
            "## 数据与分类",
            "",
            "- 分类树与观察记录：iNaturalist API（分类快照以生成日期为准）。",
            "- 分类阶元的中文名优先采用 iNaturalist zh-CN 常用名；",
            "  个别缺失时保留拉丁名，后续人工补充。",
            "- 本文件由 `scripts/08_credits.py` 自动生成，请勿手工编辑。",
            "",
        ]
    )
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(records)} records)")


if __name__ == "__main__":
    main()
