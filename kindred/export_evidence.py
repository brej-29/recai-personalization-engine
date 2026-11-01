"""Condense results/*.json into web/public/data/evidence.json, the only numbers the web app shows."""
import json
from pathlib import Path

R = Path("results")
OUT = Path("web/public/data/evidence.json")

LABEL = {
    "random": "Random",
    "popularity": "Most popular",
    "genre": "Genre overlap",
    "description_tfidf": "Plot text, TF-IDF",
    "tag_tfidf": "Tags and genres, TF-IDF",
    "zero_shot": "Sentence embedding, as is",
    "centering": "Embedding, centred per medium",
    "adapter": "Embedding + taste adapter",
    "adapter+centering": "Adapter, centred per medium",
    "fusion-no-pop": "Adapter + tags",
    "fusion-no-tag": "Adapter + popularity",
    "fusion": "Kindred: adapter + tags + popularity",
}
ORDER = list(LABEL)

CLAIMS = {
    "H1": "Sentence embeddings beat the tag, genre and popularity baselines.",
    "H2": "Centring each medium (closing the embedding gap between media) helps by at least 5%.",
    "H3": "An adapter trained on same-medium recommendations helps cross-medium by at least 10%.",
    "H4": "Kindred beats the best non-learned baseline by at least 25%.",
    "H5": "Removing the franchise filter inflates scores by 1.5x or more.",
}


def metric(s: dict, key: str = "ndcg@10") -> dict:
    m = s["summary"][key] if "summary" in s else s[key]
    return {"v": m["mean"], "lo": m["ci_low"], "hi": m["ci_high"]}


def xm() -> dict:
    d = json.loads((R / "xm.json").read_text(encoding="utf-8"))
    cm = d["hypotheses"]["chosen_model"]
    res = d["results"][cm]
    systems = [
        {"key": k, "label": LABEL[k], **metric(res[k]),
         "hit": metric(res[k], "hit@10")["v"],
         "pop": res[k]["summary"]["popularity_top_decile_share@10"]}
        for k in ORDER if k in res
    ]
    h = d["hypotheses"]
    hyp = []
    for hid in ("H1", "H2", "H3", "H4", "H5"):
        c = h["comparisons"][hid]
        row = {"id": hid, "claim": CLAIMS[hid], "supported": bool(h["supported"][hid])}
        if hid == "H5":
            row.update(filtered=c["filtered_ndcg@10"], unfiltered=c["unfiltered_ndcg@10"], ratio=c["ratio"])
        else:
            row.update(diff=c["mean_diff"], lo=c["ci_low"], hi=c["ci_high"])
            if hid in h["relative_gains"]:
                row["rel"] = h["relative_gains"][hid]
        hyp.append(row)
    sec = d["secondary_results"][cm]
    secondary = [
        {"key": k, "label": LABEL[k], **metric(sec[k])} for k in ("random", "popularity", "tag_tfidf", "zero_shot", "fusion")
    ]
    direction = {
        dn: {k: metric(v[k])["v"] for k in ("popularity", "tag_tfidf", "zero_shot", "fusion") if k in v}
        for dn, v in d["direction_breakdown"].items()
    }
    c = d["counts"]["filtered"]
    return {
        "model": cm,
        "weights": d["models"][cm]["fusion_weights"],
        "adapter_dim": d["models"][cm]["adapter"]["output_dim"],
        "queries": c["by_split"]["test"]["queries"],
        "pairs": c["by_split"]["test"]["pairs"],
        "systems": systems,
        "truth_pop": res["ground_truth"]["top_decile_share@10"],
        "hyp": hyp,
        "secondary": {"queries": d["counts"]["secondary"]["queries"], "systems": secondary},
        "direction": direction,
        "mode": d["mode"],
    }


def ml() -> dict | None:
    p = R / "ml.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    show = [s for s in d["systems"] if s in ("Popularity", "Item-kNN", "Item-kNN+pop", "Kindred", "Hybrid")
            or s.startswith("Kindred") or s == "Dense:gte-small"]
    cmp = d["h6"]["comparisons"]
    chosen = json.loads((R / "xm.json").read_text(encoding="utf-8"))["hypotheses"]["chosen_model"]
    gain = sorted(m for m, c in cmp.items() if c["ci_low"] > 0)
    loss = sorted(m for m, c in cmp.items() if c["ci_high"] < 0)
    c = cmp[f"Kindred+adapter:{chosen}"]
    h6 = {"model": chosen, "diff": c["mean_diff"], "lo": c["ci_low"], "hi": c["ci_high"],
          "gain": [m.split(":")[1] for m in gain], "loss": [m.split(":")[1] for m in loss]}
    return {
        "counts": d["counts"],
        "k": {k: {s: metric(v["metrics"][s]) for s in show if s in v["metrics"]} for k, v in d["results"].items()},
        "crossover": d["crossover"].get("k"),
        "h6": h6,
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    silo = json.loads((R / "silo.json").read_text(encoding="utf-8"))
    out = {"xm": xm(), "ml": ml(), "silo": silo}
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("evidence written", OUT.stat().st_size, "bytes; xm mode", out["xm"]["mode"])
