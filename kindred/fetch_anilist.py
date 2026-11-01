"""Fetch a bounded, popularity-ranked sample of AniList media (anime, manga, manhwa, manhua, novels).

Polite by design: <= 25 req/min, honours Retry-After, resumable, non-adult only.
Raw output goes to data/raw/ (gitignored, not redistributed).
"""
import json
import sys
import time
from pathlib import Path

import requests

URL = "https://graphql.anilist.co"
OUT = Path("data/raw/anilist")
MIN_GAP = 60 / 25  # seconds between requests

# segment -> (type, countryOfOrigin, formats, how many)
SEGMENTS = {
    "anime_tv": ("ANIME", None, ["TV", "TV_SHORT", "ONA"], 1600),
    "anime_film": ("ANIME", None, ["MOVIE"], 500),
    "manga": ("MANGA", "JP", ["MANGA", "ONE_SHOT"], 1500),
    "manhwa": ("MANGA", "KR", ["MANGA", "ONE_SHOT"], 1200),
    "manhua": ("MANGA", "CN", ["MANGA", "ONE_SHOT"], 600),
    "novel": ("MANGA", None, ["NOVEL"], 500),
}

QUERY = """
query($page:Int,$type:MediaType,$country:CountryCode,$formats:[MediaFormat]){
  Page(page:$page, perPage:50){
    pageInfo{ hasNextPage }
    media(type:$type, countryOfOrigin:$country, format_in:$formats, isAdult:false, sort:POPULARITY_DESC){
      id type format countryOfOrigin status isAdult
      title{ romaji english native }
      synonyms
      startDate{ year }
      description(asHtml:false)
      genres
      tags{ name rank isMediaSpoiler }
      averageScore popularity favourites episodes chapters volumes
      coverImage{ large color }
      siteUrl
      relations{ edges{ relationType node{ id type } } }
      recommendations(perPage:25, sort:RATING_DESC){ edges{ node{ rating mediaRecommendation{ id type isAdult } } } }
    }
  }
}
"""


def post(variables: dict) -> dict:
    while True:
        r = requests.post(URL, json={"query": QUERY, "variables": variables}, timeout=60)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "60")) + 2
            print(f"429, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code >= 500:
            time.sleep(10)
            continue
        r.raise_for_status()
        return r.json()["data"]["Page"]


def fetch(name: str) -> None:
    mtype, country, formats, limit = SEGMENTS[name]
    path = OUT / f"{name}.jsonl"
    if path.exists() and sum(1 for _ in path.open(encoding="utf-8")) >= limit:
        print(f"{name}: done")
        return
    rows, page = [], 1
    while len(rows) < limit:
        t0 = time.time()
        vars_ = {"page": page, "type": mtype, "formats": formats}
        if country:
            vars_["country"] = country  # a null variable would filter on null, not skip
        res = post(vars_)
        rows += res["media"]
        print(f"{name}: page {page}, {len(rows)} rows")
        if not res["pageInfo"]["hasNextPage"]:
            break
        page += 1
        time.sleep(max(0, MIN_GAP - (time.time() - t0)))
    with path.open("w", encoding="utf-8") as f:
        for m in rows[:limit]:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for seg in sys.argv[1:] or SEGMENTS:
        fetch(seg)
