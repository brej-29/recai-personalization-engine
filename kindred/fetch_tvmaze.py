"""Look up series posters on TVmaze by IMDb id (CC BY-SA, hot-linking allowed, 20 calls per 10 s).

Writes data/raw/tvmaze.jsonl; resumable. Attribution to TVmaze is shown in the app footer.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

OUT = Path("data/raw/tvmaze.jsonl")
UA = {"User-Agent": "kindred-research/1.0 (https://github.com/brej-29/kindred)"}
GAP = 1.0  # per-call spacing x WORKERS keeps the pool near 1.7 requests per second (limit: 20 per 10 s, a lookup costs 2)
WORKERS = 8


def lookup(imdb: str) -> dict:
    for attempt in range(8):
        try:
            r = requests.get("https://api.tvmaze.com/lookup/shows", params={"imdb": imdb}, headers=UA, timeout=20)
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(10)
            continue
        show = r.json() if r.status_code == 200 else None
        img = (show or {}).get("image") or {}
        time.sleep(GAP * WORKERS)  # each worker idles so the pool stays under 20 calls per 10 s
        return {"imdb": imdb, "tvmaze": (show or {}).get("id"), "image": img.get("medium")}
    return {"imdb": imdb, "tvmaze": None, "image": None, "error": True}


def main() -> None:
    rows = [json.loads(line) for line in Path("data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
    done = set()
    if OUT.exists():
        done = {json.loads(line)["imdb"] for line in OUT.read_text(encoding="utf-8").splitlines()}
    todo = [r["id"][3:] for r in rows if r["medium"] == "series" and r["id"][3:] not in done]
    print(len(todo), "to look up")
    with OUT.open("a", encoding="utf-8") as f, ThreadPoolExecutor(WORKERS) as pool:
        for n, rec in enumerate(pool.map(lookup, todo), 1):
            if rec.get("error"):
                continue  # not recorded, so a rerun retries it
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if n % 100 == 0:
                print(n, "/", len(todo))


if __name__ == "__main__":
    main()
