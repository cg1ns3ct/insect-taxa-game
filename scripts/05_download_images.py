"""Download one photo per target and normalize it to a modest WebP."""
from __future__ import annotations

import io
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

from inat_api import ROOT

CURATED = ROOT / "data" / "curated"
IMAGES = ROOT / "public" / "images"
IMAGES.mkdir(parents=True, exist_ok=True)
UA = "Chongjie/0.1 (insect taxonomy quiz; https://github.com/cg1ns3ct)"


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def process(record: dict) -> dict:
    photo_id = record["photo_id"]
    dest = IMAGES / f"{photo_id}.webp"
    if dest.exists():
        return {
            "taxon_id": record["taxon_id"],
            "photo_id": photo_id,
            "path": f"images/{photo_id}.webp",
            "bytes": dest.stat().st_size,
            "status": "cached",
        }

    urls = [record.get("photo_url_large"), record.get("photo_url_square")]
    urls = [u for u in urls if u]
    raw = None
    for url in urls:
        for attempt in range(2):
            try:
                raw = download(url)
                break
            except Exception:  # noqa: BLE001 - try fallback
                if attempt == 0:
                    time.sleep(0.4)
        if raw is not None:
            break
    if raw is None:
        return {
            "taxon_id": record["taxon_id"],
            "photo_id": photo_id,
            "status": "failed",
        }

    try:
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(dest, "WEBP", quality=82, method=6)
        return {
            "taxon_id": record["taxon_id"],
            "photo_id": photo_id,
            "path": f"images/{photo_id}.webp",
            "width": image.width,
            "height": image.height,
            "bytes": dest.stat().st_size,
            "status": "ok",
        }
    except Exception:  # noqa: BLE001 - corrupt image
        return {
            "taxon_id": record["taxon_id"],
            "photo_id": photo_id,
            "status": "failed",
        }


def main() -> None:
    payload = json.loads(
        (CURATED / "target_records.json").read_text(encoding="utf-8")
    )
    records = list(payload["records"].values())
    manifest: list[dict] = []
    failed: list[dict] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process, record): record for record in records}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result.get("status") == "failed":
                failed.append(result)
            else:
                manifest.append(result)
            if done % 50 == 0 or done == len(records):
                size_mb = sum(m.get("bytes", 0) for m in manifest) / 1_000_000
                print(
                    f"  {done}/{len(records)}; {size_mb:.1f} MB; failed={len(failed)}",
                    flush=True,
                )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "records": len(records),
            "manifest": len(manifest),
            "failed": len(failed),
        },
        "images": sorted(manifest, key=lambda m: m["taxon_id"]),
        "failed": failed,
    }
    (CURATED / "image_manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(out["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
