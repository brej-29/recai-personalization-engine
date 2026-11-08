"""Build the live-action catalog (movies, series) from IMDb non-commercial datasets,
Wikidata (genre, origin, enwiki title) and Wikipedia (lead text, CC BY-SA).

Raw output stays in data/raw/ (gitignored). Only embeddings and minimal metadata ship.
"""
import gzip
import json
import time
from pathlib import Path

import pandas as pd
import requests

RAW = Path("data/raw")
UA = {"User-Agent": "kindred-research/1.0 (https://github.com/brej-29/kindred)"}
MOVIE_MIN_VOTES, SERIES_MIN_VOTES = 40_000, 20_000


def imdb_candidates() -> pd.DataFrame:
    basics = pd.read_csv(
        RAW / "imdb/title.basics.tsv.gz", sep="\t", na_values=["\\N"], quoting=3,
        usecols=["tconst", "titleType", "primaryTitle", "isAdult", "startYear", "genres"],
    )
    ratings = pd.read_csv(RAW / "imdb/title.ratings.tsv.gz", sep="\t")
    df = basics.merge(ratings, on="tconst")
    df = df[(df.isAdult == 0) & df.titleType.isin(["movie", "tvSeries", "tvMiniSeries"])]
    keep = ((df.titleType == "movie") & (df.numVotes >= MOVIE_MIN_VOTES)) | (
        (df.titleType != "movie") & (df.numVotes >= SERIES_MIN_VOTES)
    )
    return df[keep].reset_index(drop=True)


def _get_json(url: str, params: dict, headers: dict) -> dict:
    for attempt in range(8):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=90)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(min(60, 5 * (attempt + 1)))
    raise RuntimeError(f"giving up on {url}")


def wikidata(ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 150):
        vals = " ".join(f'"{x}"' for x in ids[i : i + 150])
        q = f"""SELECT ?imdb ?title (GROUP_CONCAT(DISTINCT ?g; separator="|") AS ?genres)
        (GROUP_CONCAT(DISTINCT ?o; separator="|") AS ?origins) WHERE {{
          VALUES ?imdb {{ {vals} }}
          ?item wdt:P345 ?imdb .
          ?a schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?title .
          OPTIONAL {{ ?item wdt:P136 ?gi . ?gi rdfs:label ?g FILTER(lang(?g)="en") }}
          OPTIONAL {{ ?item wdt:P495 ?oi . ?oi rdfs:label ?o FILTER(lang(?o)="en") }}
        }} GROUP BY ?imdb ?title"""
        r = _get_json("https://query.wikidata.org/sparql", {"query": q},
                      {**UA, "Accept": "application/sparql-results+json"})
        for b in r["results"]["bindings"]:
            out[b["imdb"]["value"]] = {
                "wiki": b["title"]["value"],
                "wd_genres": [x for x in b["genres"]["value"].split("|") if x],
                "origins": [x for x in b["origins"]["value"].split("|") if x],
            }
        print(f"wikidata {min(i + 150, len(ids))}/{len(ids)}")
        time.sleep(1)
    return out


def extracts(titles: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(titles), 20):
        chunk = titles[i : i + 20]
        r = _get_json(
            "https://en.wikipedia.org/w/api.php", 
            {"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                    "exlimit": 20, "redirects": 1, "format": "json", "formatversion": 2,
                    "titles": "|".join(chunk)}, UA,
        )
        q = r["query"]
        alias = {}
        for k in ("normalized", "redirects"):
            for m in q.get(k, []):
                alias[m["from"]] = m["to"]
        by_title = {p["title"]: p.get("extract", "") for p in q["pages"]}
        for t in chunk:
            cur = t
            for _ in range(3):
                cur = alias.get(cur, cur)
            out[t] = by_title.get(cur, "")
        if i // 20 % 25 == 0:
            print(f"wikipedia {min(i + 20, len(titles))}/{len(titles)}")
        time.sleep(0.5)
    return out


if __name__ == "__main__":
    cand = imdb_candidates()
    print(len(cand), "IMDb candidates")
    wd = wikidata(cand.tconst.tolist())
    cand = cand[cand.tconst.isin(wd)].copy()
    ex = extracts([wd[t]["wiki"] for t in cand.tconst])
    rows = []
    for r in cand.itertuples():
        w = wd[r.tconst]
        rows.append({
            "imdb": r.tconst, "kind": "movie" if r.titleType == "movie" else "series",
            "title": r.primaryTitle, "year": None if pd.isna(r.startYear) else int(r.startYear),
            "genres": (r.genres or "").split(",") if isinstance(r.genres, str) else [],
            "wd_genres": w["wd_genres"], "origins": w["origins"], "wiki": w["wiki"],
            "rating": float(r.averageRating), "votes": int(r.numVotes),
            "text": ex[w["wiki"]],
        })
    with gzip.open(RAW / "live_action.jsonl.gz", "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(len(rows), "rows written")
