"""Pack the catalogue, final embeddings and atlas into compact static files for the web app."""
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path("web/public/data")
MEDIA = ["anime", "anime-film", "manga", "manhwa", "manhua", "novel", "movie", "series"]
COVER_PREFIX = "https://s4.anilist.co/file/anilistcdn/media/"


def pack(emb_path: str, atlas_path: str = "data/atlas.npy") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in Path("data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
    genres: dict[str, int] = {}
    tags: dict[str, int] = {}
    comps: dict[str, int] = {}

    def idx(table: dict[str, int], name: str) -> int:
        return table.setdefault(name, len(table))

    cat = {k: [] for k in ["id", "t", "a", "f", "m", "y", "s", "p", "g", "k", "c", "col", "u"]}
    for r in rows:
        cover = r["cover"] or ""
        cat["id"].append(r["id"])
        cat["t"].append(r["title"])
        alt = r["alt"] if r["alt"] and r["alt"] != r["title"] else ""
        cat["a"].append(alt)
        cat["f"].append(idx(comps, r["comp"]))
        cat["m"].append(MEDIA.index(r["medium"]))
        cat["y"].append(r["year"] or 0)
        cat["s"].append(r["score"] or 0)
        cat["p"].append(r["pop"] or 0)
        cat["g"].append([idx(genres, g) for g in r["genres"][:5]])
        cat["k"].append([idx(tags, t["n"]) for t in r["tags"][:6]])
        cat["c"].append(cover.removeprefix(COVER_PREFIX))
        cat["col"].append((r["color"] or "").lstrip("#"))
        cat["u"].append(r["url"].removeprefix("https://anilist.co/").removeprefix("https://www.imdb.com/title/"))
    cat.update(media=MEDIA, genres=list(genres), tags=list(tags), n=len(rows))
    (OUT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    emb = np.load(emb_path).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    q = np.round(emb * 127).astype(np.int8)
    (OUT / "emb.bin").write_bytes(q.tobytes())
    xy = np.load(atlas_path)
    (OUT / "atlas.bin").write_bytes((xy * 65535).astype(np.uint16).tobytes())
    (OUT / "meta.json").write_text(json.dumps({"n": len(rows), "d": emb.shape[1], "emb": Path(emb_path).name}))
    print("packed", len(rows), emb.shape)


if __name__ == "__main__":
    pack(sys.argv[1] if len(sys.argv) > 1 else "data/emb/minilm.npy")
