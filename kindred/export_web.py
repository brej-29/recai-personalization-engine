"""Pack the catalogue, the final Kindred vectors and the tag channel into static files for the web app.

The browser runs the same scoring as kindred.engine: score = a*cos(dense) + b*cos(tags) + c*popularity z-score.
`reference_recommend` mirrors the TypeScript engine on the shipped (quantised) arrays; its output is written
to web/src/fixtures/parity.json and checked by the web tests.
"""
import json
import math
from pathlib import Path

import numpy as np

OUT = Path("web/public/data")
MEDIA = ["anime", "anime-film", "manga", "manhwa", "manhua", "novel", "movie", "series"]
COVER_PREFIX = "https://s4.anilist.co/file/anilistcdn/media/"


def load_rows() -> list[dict]:
    return [json.loads(line) for line in Path("data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]


def pack_catalog(rows: list[dict]) -> dict:
    genres: dict[str, int] = {}
    tags: dict[str, int] = {}
    comps: dict[str, int] = {}

    def idx(table: dict[str, int], name: str) -> int:
        return table.setdefault(name, len(table))

    cat = {k: [] for k in ["id", "t", "a", "f", "m", "y", "s", "p", "g", "k", "c", "col"]}
    for r in rows:
        cat["id"].append(r["id"])
        cat["t"].append(r["title"])
        cat["a"].append(r["alt"] if r["alt"] and r["alt"] != r["title"] else "")
        cat["f"].append(idx(comps, r["comp"]))
        cat["m"].append(MEDIA.index(r["medium"]))
        cat["y"].append(r["year"] or 0)
        cat["s"].append(r["score"] or 0)
        cat["p"].append(r["pop"] or 0)
        cat["g"].append([idx(genres, g) for g in r["genres"][:5]])
        cat["k"].append([idx(tags, t["n"]) for t in r["tags"][:6]])
        cat["c"].append((r["cover"] or "").removeprefix(COVER_PREFIX))
        cat["col"].append((r["color"] or "").lstrip("#"))
    cat.update(media=MEDIA, genres=list(genres), tags=list(tags), n=len(rows))
    return cat


def dequant(q: np.ndarray) -> np.ndarray:
    return q.astype(np.float32) / 127.0


def popularity_z(rows: list[dict]) -> np.ndarray:
    """z-score of log1p(pop) within each family: AniList popularity and IMDb votes are not comparable."""
    lp = np.log1p(np.array([r["pop"] or 0 for r in rows], dtype=np.float32))
    fam = np.array([r["family"] for r in rows])
    z = np.zeros_like(lp)
    for f in np.unique(fam):
        m = fam == f
        z[m] = (lp[m] - lp[m].mean()) / max(float(lp[m].std()), 1e-6)
    return z.astype(np.float16)


def reference_recommend(
    emb: np.ndarray, tag_indptr, tag_indices, tag_data, popz, cat: dict, w: dict,
    seeds: list[int], media: int | None, hide_franchise: bool = True, k: int = 10,
) -> list[int]:
    """Python twin of web/src/engine.ts (same arrays, same rules)."""
    n = emb.shape[0]
    q = emb[seeds].sum(axis=0)
    q /= max(float(np.linalg.norm(q)), 1e-12)
    dense = emb @ q
    tq = np.zeros(int(max(tag_indices)) + 1, dtype=np.float32)
    for s in seeds:
        sl = slice(tag_indptr[s], tag_indptr[s + 1])
        tq[tag_indices[sl]] += tag_data[sl].astype(np.float32)
    tq /= len(seeds)
    tag = np.array(
        [float((tq[tag_indices[tag_indptr[i]:tag_indptr[i + 1]]] * tag_data[tag_indptr[i]:tag_indptr[i + 1]]).sum())
         for i in range(n)], dtype=np.float32)
    score = w["a"] * dense + w["b"] * tag + w["c"] * popz.astype(np.float32)
    fr = {cat["f"][s] for s in seeds}
    seed_set = set(seeds)
    cap = k if media is not None else math.ceil(k / 4)
    used = [0] * len(MEDIA)
    seen: set[int] = set()
    order = [int(i) for i in np.argsort(-score, kind="stable")
             if int(i) not in seed_set and (media is None or cat["m"][int(i)] == media)
             and not (hide_franchise and cat["f"][int(i)] in fr)]
    picked: list[int] = []

    def take(i: int) -> None:
        seen.add(cat["f"][i])
        used[cat["m"][i]] += 1
        picked.append(i)

    if media is None:  # pass 1: the best title of every shelf
        have: set[int] = set()
        for i in order:
            if cat["m"][i] in have or cat["f"][i] in seen:
                continue
            have.add(cat["m"][i])
            take(i)
            if len(have) == len(MEDIA):
                break
    for i in order:
        if len(picked) >= k:
            break
        if i in picked or used[cat["m"][i]] >= cap or cat["f"][i] in seen:
            continue
        take(i)
    out = sorted(picked, key=lambda i: (-float(score[i]), i))
    return out


def pack(atlas_from_final: bool = True) -> None:
    from kindred.engine import KindredEngine
    from kindred.eval.baselines import build_text_features

    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    res = json.loads(Path("results/xm.json").read_text(encoding="utf-8"))
    model = res["hypotheses"]["chosen_model"]
    w = res["models"][model]["fusion_weights"]
    w = {k: float(v) for k, v in w.items()}
    emb0 = np.load(f"data/emb/{model}.npy").astype(np.float32)
    adapter = np.load(f"results/adapter_{model}.npz")["W"]
    final = KindredEngine(rows, emb0, adapter=adapter, centered=bool(w.get("centered"))).embeddings

    q = np.round(final * 127).astype(np.int8)
    emb = dequant(q)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    (OUT / "emb.bin").write_bytes(q.tobytes())

    tag = build_text_features(rows).tags.tocsr()
    tag.sort_indices()
    td = tag.data.astype(np.float16)
    (OUT / "tags_indptr.bin").write_bytes(tag.indptr.astype(np.uint32).tobytes())
    (OUT / "tags_indices.bin").write_bytes(tag.indices.astype(np.uint16).tobytes())
    (OUT / "tags_data.bin").write_bytes(td.tobytes())

    popz = popularity_z(rows)
    (OUT / "popz.bin").write_bytes(popz.tobytes())

    atlas_path = Path("data/atlas.npy")
    if atlas_from_final:
        from kindred.atlas import project

        np.save(atlas_path, project(final))
    xy = np.load(atlas_path)
    (OUT / "atlas.bin").write_bytes((xy * 65535).astype(np.uint16).tobytes())

    cat = pack_catalog(rows)
    (OUT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meta = {"n": len(rows), "d": int(emb.shape[1]), "model": model, "weights": w, "nnz": int(tag.nnz),
            "tag_vocab": int(tag.shape[1])}
    (OUT / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    rng = np.random.default_rng(13)
    titles = [("Frieren", None), ("Solo Leveling", None), ("Parasite", None), ("Death Note", 2), ("Berserk", 6)]
    cases = []
    for t, media in titles:
        i = next(j for j, r in enumerate(rows) if r["title"].lower().startswith(t.lower()))
        cases.append({"seeds": [i], "media": media})
    for _ in range(4):
        cases.append({"seeds": [int(x) for x in rng.choice(len(rows), 3, replace=False)], "media": None})
    for c in cases:
        c["expected"] = reference_recommend(
            emb, tag.indptr, tag.indices, td, popz, cat, w, c["seeds"], c["media"], True, 12)
    fx = Path("web/src/fixtures")
    fx.mkdir(parents=True, exist_ok=True)
    (fx / "parity.json").write_text(json.dumps(cases), encoding="utf-8")
    print("packed", len(rows), emb.shape, "tags nnz", tag.nnz, "weights", w)


if __name__ == "__main__":
    import sys

    pack(atlas_from_final="--keep-atlas" not in sys.argv)
