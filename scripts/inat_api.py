"""Small cached client for the public iNaturalist API.

The game is built offline. Every response is cached under data/raw/inat so the
pipeline can be re-run without hammering the API.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "inat"
CACHE.mkdir(parents=True, exist_ok=True)

API = "https://api.inaturalist.org/v1"
USER_AGENT = "Chongjie/0.1 (insect taxonomy quiz; https://github.com/cg1ns3ct)"
DELAY = 0.8
MIN_INTERVAL = 0.7
_RATE_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


def _wait_for_slot() -> None:
    """A process-wide, thread-safe polite rate limit."""
    global _LAST_REQUEST
    with _RATE_LOCK:
        now = time.monotonic()
        wait = MIN_INTERVAL - (now - _LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST = time.monotonic()


def _cache_path(url: str) -> Path:
    return CACHE / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".json")


def get(path: str, params: dict | None = None, *, refresh: bool = False) -> dict:
    params = params or {}
    query = urllib.parse.urlencode(sorted(params.items()))
    url = f"{API}{path}" + (f"?{query}" if query else "")
    cache = _cache_path(url)
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))

    last_error: Exception | None = None
    for attempt in range(6):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        try:
            _wait_for_slot()
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.load(response)
            cache.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return data
        except urllib.error.HTTPError as exc:
            last_error = exc
            # 429/5xx are transient. 422 has sometimes appeared when requests
            # arrive too quickly, so back off rather than giving up immediately.
            if exc.code in (429, 500, 502, 503, 504, 422):
                wait = min(60, 5 * (attempt + 1))
                print(f"  HTTP {exc.code}; retrying in {wait}s ({path})")
                time.sleep(wait)
                continue
            body = exc.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc
        except Exception as exc:  # noqa: BLE001 - network retry
            last_error = exc
            wait = min(30, 3 * (attempt + 1))
            print(f"  {type(exc).__name__}: {exc}; retrying in {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"Failed after retries: {url}") from last_error


def paginate(path: str, params: dict, *, max_pages: int = 200) -> list[dict]:
    """Fetch all pages for an endpoint that returns {total_results, results}."""
    results: list[dict] = []
    page = 1
    total = None
    while page <= max_pages:
        data = get(path, {**params, "page": page})
        if total is None:
            total = data.get("total_results", 0)
        batch = data.get("results", [])
        results.extend(batch)
        print(f"  page {page}: +{len(batch)} / {total}")
        if not batch or len(results) >= total:
            break
        page += 1
    return results


def batch_taxa(ids: list[int], *, chunk: int = 100) -> dict[int, dict]:
    """Fetch taxa by id in batches. Returns id -> taxon object."""
    out: dict[int, dict] = {}
    unique = sorted({int(i) for i in ids if i})
    for start in range(0, len(unique), chunk):
        part = unique[start : start + chunk]
        data = get(
            "/taxa",
            {
                "id": ",".join(str(i) for i in part),
                "per_page": len(part),
                "locale": "zh-CN",
            },
        )
        for taxon in data.get("results", []):
            out[int(taxon["id"])] = taxon
        print(f"  taxa {start + len(part)}/{len(unique)}")
    return out


def children(parent_id: int, rank: str | None = None, *, per_page: int = 200) -> list[dict]:
    params: dict[str, str | int] = {
        "parent_id": parent_id,
        "per_page": per_page,
        "locale": "zh-CN",
    }
    if rank:
        params["rank"] = rank
    return paginate("/taxa", params, max_pages=10)


def descendants(
    taxon_id: int,
    rank: str,
    *,
    per_page: int = 200,
    order_by: str | None = None,
    max_pages: int = 5,
) -> list[dict]:
    params: dict[str, str | int] = {
        "taxon_id": taxon_id,
        "rank": rank,
        "per_page": per_page,
        "locale": "zh-CN",
    }
    if order_by:
        params["order_by"] = order_by
    return paginate("/taxa", params, max_pages=max_pages)
