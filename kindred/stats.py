"""Silo statistics: how many AniList user recommendations cross media types? -> results/silo.json"""
import json
from collections import Counter
from pathlib import Path

MIN_RATING = 2


def main() -> dict:
    rows = [json.loads(line) for line in Path("data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
    al = {r["_aid"]: r for r in rows if "_aid" in r}
    def typ(r: dict) -> str:  # AniList's own media type
        return "ANIME" if r["family"] == "anime" else "MANGA"

    fine = Counter()
    n_same = n_cross_type = n_cross_format = 0
    for r in al.values():
        for j, rating in r["_rec"]:
            t = al.get(j)
            if t is None or rating < MIN_RATING:
                continue
            fine[(r["medium"], t["medium"])] += 1
            if typ(r) != typ(t):
                n_cross_type += 1
            elif r["medium"] == t["medium"] or (r["family"] == "anime" and t["family"] == "anime"):
                n_same += 1
            else:
                n_cross_format += 1
    has_source = sum(
        1 for r in al.values() if r["family"] == "anime"
        and any(rt in ("ADAPTATION", "SOURCE") and j in al and al[j]["family"] == "print" for j, rt in r["_relt"])
    )
    out = {
        "min_rating": MIN_RATING,
        "titles": len(al),
        "rec_edges_same_format": n_same,
        "rec_edges_cross_format_within_manga_type": n_cross_format,
        "rec_edges_anime_to_print_or_back": n_cross_type,
        "anime_with_print_source_in_sample": has_source,
        "by_medium_pair": {f"{a}>{b}": c for (a, b), c in sorted(fine.items())},
        "note": "AniList only lets users recommend within one media type (ANIME or MANGA).",
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/silo.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps({k: v for k, v in main().items() if k != "by_medium_pair"}, indent=1))
