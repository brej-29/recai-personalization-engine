"""Merge raw AniList + live-action pulls into one catalogue (data/catalog.jsonl).

Each row: id, medium, family, title, year, genres, tags, text (encoder input, title-free),
score, popularity, cover, color, url, comp (relation-graph component), plus raw counts.
"""
import gzip
import html
import json
import re
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/catalog.jsonl")

SEG_MEDIUM = {
    "anime_tv": "anime", "anime_film": "anime-film", "manga": "manga",
    "manhwa": "manhwa", "manhua": "manhua", "novel": "novel",
}
FAMILY = {"anime": "anime", "anime-film": "anime", "manga": "print", "manhwa": "print",
          "manhua": "print", "novel": "print", "movie": "live", "series": "live"}


def clean(text: str | None, limit: int = 1200) -> str:
    t = html.unescape(text or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\(Source:[^)]*\)|\[Written by[^\]]*\]|Note:.*$", " ", t, flags=re.DOTALL)
    return re.sub(r"\s+", " ", t).strip()[:limit]


def mk_text(desc: str, genres: list[str], themes: list[str]) -> str:
    parts = [desc]
    if genres:
        parts.append("Genres: " + ", ".join(genres) + ".")
    if themes:
        parts.append("Themes: " + ", ".join(themes) + ".")
    return " ".join(parts)


def load_anilist() -> tuple[list[dict], dict[int, set[int]]]:
    rows, links = [], {}
    for seg, medium in SEG_MEDIUM.items():
        for line in (RAW / f"anilist/{seg}.jsonl").open(encoding="utf-8"):
            m = json.loads(line)
            themes = [t["name"] for t in sorted(m["tags"], key=lambda t: -t["rank"])
                      if t["rank"] >= 40 and not t["isMediaSpoiler"]][:12]
            t = m["title"]
            rows.append({
                "id": f"al:{m['id']}", "medium": medium, "family": FAMILY[medium],
                "title": t["english"] or t["romaji"] or t["native"], "alt": t["romaji"],
                "year": (m["startDate"] or {}).get("year"), "genres": m["genres"],
                "tags": [{"n": x["name"], "r": x["rank"]} for x in m["tags"]
                         if x["rank"] >= 40 and not x["isMediaSpoiler"]][:12],
                "text": mk_text(clean(m["description"]), m["genres"], themes),
                "score": m["averageScore"], "pop": m["popularity"],
                "cover": (m["coverImage"] or {}).get("large"),
                "color": (m["coverImage"] or {}).get("color"), "url": m["siteUrl"],
                "_aid": m["id"],
                "_rel": [e["node"]["id"] for e in m["relations"]["edges"]],
                "_rec": [(e["node"]["mediaRecommendation"]["id"], e["node"]["rating"])
                         for e in m["recommendations"]["edges"]
                         if e["node"]["mediaRecommendation"] and e["node"]["rating"] is not None],
                "_relt": [(e["node"]["id"], e["relationType"]) for e in m["relations"]["edges"]],
            })
    return rows, links


def is_anime_dup(r: dict) -> bool:
    wd = " ".join(r["wd_genres"]).lower()
    return "anime" in wd or ("Animation" in r["genres"] and "Japan" in r["origins"])


def drop_first_sentence(text: str) -> str:
    """Wikipedia leads open with 'X is a 1994 American ... film directed by ... starring ...':
    title and cast, not taste. Genres come from structured fields instead."""
    rest = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text, maxsplit=1)
    return rest[1] if len(rest) == 2 else ""


def tvmaze_posters() -> dict[str, str]:
    path = RAW / "tvmaze.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("image"):
            out[r["imdb"]] = r["image"]
    return out


def load_live() -> list[dict]:
    posters = tvmaze_posters()
    rows = []
    with gzip.open(RAW / "live_action.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            body = drop_first_sentence(r["text"])
            if len(body) < 80 or is_anime_dup(r):
                continue
            r["text"] = body
            genres = sorted(set(r["genres"]) | {g.title() for g in r["wd_genres"][:3]})
            rows.append({
                "id": f"im:{r['imdb']}", "medium": r["kind"], "family": "live",
                "title": r["title"], "alt": None, "year": r["year"], "genres": r["genres"],
                "tags": [], "text": mk_text(clean(r["text"], 1400), genres, []),
                "score": round(r["rating"] * 10), "pop": r["votes"],
                "cover": posters.get(r["imdb"]) if r["kind"] == "series" else None,
                "color": None, "url": f"https://www.imdb.com/title/{r['imdb']}/",
            })
    return rows


def components(rows: list[dict]) -> None:
    parent = {r["_aid"]: r["_aid"] for r in rows if "_aid" in r}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in rows:
        for j in r.get("_rel", []):
            if j in parent:
                parent[find(r["_aid"])] = find(j)
    for r in rows:
        r["comp"] = f"al:{find(r['_aid'])}" if "_aid" in r else r["id"]


if __name__ == "__main__":
    al, _ = load_anilist()
    live = load_live() if (RAW / "live_action.jsonl.gz").exists() else []
    rows = al + live
    components(rows)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(len(rows), Counter(r["medium"] for r in rows))
