"""Run the preregistered XM evaluation.

The default invocation scores validation only.  ``--final`` additionally scores the
held-out test split using choices made on validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from kindred.engine import KindredEngine
from kindred.eval.adapter import AdapterResult, save_adapter, train_adapter
from kindred.eval.baselines import (
    TextFeatures,
    build_text_features,
    popularity_percentiles,
    rank_baseline,
)
from kindred.eval.metrics import (
    bootstrap_mean_ci,
    catalogue_coverage,
    mean_popularity_percentile,
    paired_bootstrap,
    query_metric_arrays,
)
from kindred.eval.pairs import (
    PairSet,
    Query,
    build_secondary_pairs,
    build_xm_pairs,
    load_catalog,
    same_type_training_edges,
)

SEED = 13
BOOTSTRAP = 10_000
K = 10
BASELINES = ("random", "popularity", "genre", "tag_tfidf", "description_tfidf")


def _queries(pair_set: PairSet, split: str) -> list[Query]:
    return [query for query in pair_set.queries if query.split == split]


def _engine_rankings(
    engine: KindredEngine, rows: list[dict], queries: list[Query], k: int = K
) -> list[np.ndarray]:
    rankings = [np.asarray([], dtype=int) for _ in queries]
    by_family: dict[str, list[int]] = {}
    for position, query in enumerate(queries):
        if query.candidates:
            by_family.setdefault(rows[query.candidates[0]].get("family", ""), []).append(position)
    for family, positions in by_family.items():
        all_candidates = engine._candidate_indices(family)
        candidate_position = {int(item): index for index, item in enumerate(all_candidates)}
        query_indices = np.asarray([queries[position].query_idx for position in positions], dtype=int)
        dense_scores = engine.embeddings[query_indices] @ engine.embeddings[all_candidates].T
        tag_scores = None
        if engine.tag_features is not None and engine.weights.get("b", 0.0):
            tag_product = engine.tag_features[query_indices] @ engine.tag_features[all_candidates].T
            tag_scores = np.asarray(
                tag_product.toarray() if hasattr(tag_product, "toarray") else tag_product
            )
        for row_number, position in enumerate(positions):
            query = queries[position]
            local_positions = np.asarray([candidate_position[item] for item in query.candidates])
            score = engine.weights.get("a", 0.0) * dense_scores[row_number, local_positions]
            if tag_scores is not None:
                score = score + engine.weights.get("b", 0.0) * tag_scores[row_number, local_positions]
            pop = engine.log_pop[np.asarray(query.candidates)]
            pop_prior = (pop - pop.mean()) / max(float(pop.std()), 1e-12)
            score = score + engine.weights.get("c", 0.0) * pop_prior
            order = np.argsort(-score, kind="mergesort")[:k]
            rankings[position] = np.asarray(query.candidates, dtype=int)[order]
    return rankings


def _baseline_rankings(
    system: str,
    rows: list[dict],
    features: TextFeatures,
    queries: list[Query],
    embeddings: np.ndarray,
) -> list[np.ndarray]:
    rng = np.random.default_rng(SEED)
    return [
        rank_baseline(
            system, query.query_idx, query.candidates, rows, features,
            embeddings=embeddings, rng=rng, k=K
        )
        for query in queries
    ]


def _summary(
    rankings: list[np.ndarray], queries: list[Query], rows: list[dict], percentiles: np.ndarray
) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    relevant = [set(query.relevant) for query in queries]
    arrays = query_metric_arrays(rankings, relevant, K)
    result: dict[str, object] = {}
    for name, values in arrays.items():
        result[name] = bootstrap_mean_ci(values, BOOTSTRAP, SEED)
    pool_items = {item for query in queries for item in query.candidates}
    result["coverage@10"] = (
        catalogue_coverage(rankings, K) / len(pool_items) if pool_items else 0.0
    )
    result["mean_popularity_percentile@10"] = mean_popularity_percentile(
        rankings, percentiles, K
    )
    result["popularity_top_decile_share@10"] = _top_decile_share(
        rankings, percentiles, K
    )
    result["n_queries"] = len(queries)
    return result, arrays


def _top_decile_share(
    rankings: list[np.ndarray], percentiles: np.ndarray, k: int = K
) -> float:
    items = [int(item) for ranking in rankings for item in ranking[:k]]
    return float(np.mean([percentiles[item] >= 0.9 for item in items])) if items else 0.0


def _ground_truth_decile_share(
    queries: list[Query], percentiles: np.ndarray
) -> float:
    items = [item for query in queries for item in query.relevant]
    return float(np.mean([percentiles[item] >= 0.9 for item in items])) if items else 0.0


def _evaluate_systems(
    rows: list[dict],
    embeddings: np.ndarray,
    features: TextFeatures,
    pair_set: PairSet,
    split: str,
    engines: dict[str, KindredEngine],
    percentiles: np.ndarray,
) -> dict[str, dict[str, object]]:
    queries = _queries(pair_set, split)
    output = {}
    for system in BASELINES:
        rankings = _baseline_rankings(system, rows, features, queries, embeddings)
        summary, arrays = _summary(rankings, queries, rows, percentiles)
        output[system] = {"summary": summary, "arrays": arrays, "rankings": rankings}
    for system, engine in engines.items():
        rankings = _engine_rankings(engine, rows, queries)
        summary, arrays = _summary(rankings, queries, rows, percentiles)
        output[system] = {"summary": summary, "arrays": arrays, "rankings": rankings}
    output["ground_truth"] = {"top_decile_share@10": _ground_truth_decile_share(queries, percentiles)}
    return output


def _fusion_engine(rows, embeddings, features, adapter, weights) -> KindredEngine:
    return KindredEngine(
        rows, embeddings, tag_features=features.tags, centered=bool(weights.get("centered", 0.0)),
        adapter=adapter.matrix, weights=weights,
    )


def _make_engines(
    rows: list[dict],
    embeddings: np.ndarray,
    features: TextFeatures,
    adapter: AdapterResult,
    weights: dict[str, float],
) -> dict[str, KindredEngine]:
    return {
        "zero_shot": KindredEngine(rows, embeddings),
        "centering": KindredEngine(rows, embeddings, centered=True),
        "adapter": KindredEngine(rows, embeddings, adapter=adapter.matrix),
        "adapter+centering": KindredEngine(
            rows, embeddings, centered=True, adapter=adapter.matrix
        ),
        "fusion": _fusion_engine(rows, embeddings, features, adapter, weights),
        "fusion-no-pop": _fusion_engine(rows, embeddings, features, adapter, {**weights, "c": 0.0}),
        "fusion-no-tag": _fusion_engine(rows, embeddings, features, adapter, {**weights, "b": 0.0}),
    }


def _choose_fusion(
    rows: list[dict],
    embeddings: np.ndarray,
    features: TextFeatures,
    adapter: AdapterResult,
    pair_set: PairSet,
    percentiles: np.ndarray,
) -> tuple[dict[str, float], float]:
    queries = _queries(pair_set, "val")
    best = (-np.inf, {"a": 1.0, "b": 0.0, "c": 0.0, "centered": 0.0})
    for centered in (0.0, 1.0):  # centering is a val-chosen switch: it did not help on its own
        for a in (0.5, 1.0, 1.5, 2.0):
            for b in (0.0, 0.15, 0.3, 0.5):
                for c in (0.0, 0.1, 0.2):
                    w = {"a": a, "b": b, "c": c, "centered": centered}
                    engine = _fusion_engine(rows, embeddings, features, adapter, w)
                    rankings = _engine_rankings(engine, rows, queries)
                    arrays = query_metric_arrays(rankings, [set(q.relevant) for q in queries], K)
                    score = float(arrays["ndcg@10"].mean()) if queries else 0.0
                    if score > best[0]:
                        best = (score, w)
    return best[1], float(best[0])


def _json_summary(value):
    if isinstance(value, dict):
        return {key: _json_summary(item) for key, item in value.items() if key not in {"arrays", "rankings"}}
    if isinstance(value, list):
        return [_json_summary(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _paired(
    systems: dict[str, dict[str, object]], first: str, second: str, metric: str = "ndcg@10"
) -> dict[str, float]:
    if first not in systems or second not in systems:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    return paired_bootstrap(
        systems[first]["arrays"][metric], systems[second]["arrays"][metric], BOOTSTRAP, SEED
    )


def _hypotheses(
    primary: dict[str, dict[str, object]],
    no_filter: dict[str, dict[str, object]],
    chosen_model: str,
) -> dict[str, object]:
    model = primary[chosen_model]
    non_dense = [name for name in BASELINES if name != "random"]
    best_non_dense = max(non_dense, key=lambda name: model[name]["summary"]["ndcg@10"]["mean"])
    best_zero = "zero_shot"
    best_non_learned = max(
        [*BASELINES, "zero_shot"],
        key=lambda name: model[name]["summary"]["ndcg@10"]["mean"],
    )
    comparisons = {
        "H1": _paired(model, best_zero, best_non_dense),
        "H2": _paired(model, "centering", best_zero),
        "H3": _paired(model, "adapter", best_zero),
        "H4": _paired(model, "fusion", best_non_learned),
    }
    h5_filtered = model["zero_shot"]["summary"]["ndcg@10"]["mean"]
    h5_unfiltered = no_filter[chosen_model]["zero_shot"]["summary"]["ndcg@10"]["mean"]
    comparisons["H5"] = {
        "filtered_ndcg@10": h5_filtered,
        "unfiltered_ndcg@10": h5_unfiltered,
        "ratio": h5_unfiltered / h5_filtered if h5_filtered else float("inf"),
        "mean_diff": h5_unfiltered - h5_filtered,
        "ci_low": 0.0,
        "ci_high": 0.0,
        "n": no_filter[chosen_model]["zero_shot"]["summary"]["n_queries"],
    }
    gain_h2 = comparisons["H2"]["mean_diff"] / max(
        1e-12, model[best_zero]["summary"]["ndcg@10"]["mean"]
    )
    gain_h3 = comparisons["H3"]["mean_diff"] / max(
        1e-12, model[best_zero]["summary"]["ndcg@10"]["mean"]
    )
    gain_h4 = comparisons["H4"]["mean_diff"] / max(
        1e-12, model[best_non_learned]["summary"]["ndcg@10"]["mean"]
    )
    supported = {
        "H1": comparisons["H1"]["ci_low"] > 0,
        "H2": gain_h2 >= 0.05 and comparisons["H2"]["ci_low"] > 0,
        "H3": gain_h3 >= 0.10 and comparisons["H3"]["ci_low"] > 0,
        "H4": gain_h4 >= 0.25 and comparisons["H4"]["ci_low"] > 0,
        "H5": comparisons["H5"]["ratio"] >= 1.5,
    }
    return {
        "chosen_model": chosen_model,
        "best_non_dense": best_non_dense,
        "best_non_learned": best_non_learned,
        "comparisons": comparisons,
        "relative_gains": {"H2": gain_h2, "H3": gain_h3, "H4": gain_h4},
        "supported": supported,
    }


def _direction_breakdown(
    systems: dict[str, dict[str, object]], queries: list[Query], rows: list[dict], percentiles: np.ndarray
) -> dict[str, object]:
    output = {}
    for direction in sorted({query.direction for query in queries}):
        indices = [i for i, query in enumerate(queries) if query.direction == direction]
        output[direction] = {}
        for system, value in systems.items():
            if system == "ground_truth":
                continue
            selected = [value["rankings"][i] for i in indices]
            selected_queries = [queries[i] for i in indices]
            summary, _ = _summary(selected, selected_queries, rows, percentiles)
            output[direction][system] = summary
    return output


def _write_errors(
    path: Path,
    rows: list[dict],
    queries: list[Query],
    rankings: list[np.ndarray],
    seed: int = SEED,
) -> None:
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(queries), size=min(15, len(queries)), replace=False) if queries else []
    lines = ["# XM error analysis", "", "Top five predictions from the selected full system.", ""]
    for position in chosen:
        query = queries[int(position)]
        lines.append(f"## Query: {rows[query.query_idx].get('title', query.query_idx)}")
        lines.append("Relevant: " + "; ".join(rows[i].get("title", str(i)) for i in query.relevant))
        lines.append("Predicted: " + "; ".join(rows[i].get("title", str(i)) for i in rankings[int(position)][:5]))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _headline_table(results: dict[str, dict[str, object]]) -> str:
    lines = ["| System | NDCG@10 | 95% CI |", "|---|---:|---:|"]
    for name, value in results.items():
        if name == "ground_truth":
            continue
        metric = value["summary"]["ndcg@10"]
        lines.append(f"| {name} | {metric['mean']:.4f} | [{metric['ci_low']:.4f}, {metric['ci_high']:.4f}] |")
    return "\n".join(lines)


def run(final: bool = False) -> dict[str, object]:
    rows = load_catalog()
    embeddings_dir = Path("data/emb")
    embedding_paths = sorted(embeddings_dir.glob("*.npy"))
    if not embedding_paths:
        raise FileNotFoundError("no embedding files found in data/emb")
    features = build_text_features(rows)
    percentiles = popularity_percentiles(rows)
    primary, component_split = build_xm_pairs(rows, SEED, filter_components=True)
    no_filter, _ = build_xm_pairs(rows, SEED, filter_components=False)
    secondary = build_secondary_pairs(rows, component_split, filter_components=True)
    print("XM counts:", json.dumps(primary.counts, sort_keys=True))
    print("XM without component filter:", json.dumps(no_filter.counts, sort_keys=True))
    print("Secondary counts:", json.dumps(secondary.counts, sort_keys=True))

    model_data: dict[str, object] = {}
    validation_results: dict[str, dict[str, object]] = {}
    test_results: dict[str, dict[str, object]] = {}
    no_filter_results: dict[str, dict[str, object]] = {}
    adapters: dict[str, AdapterResult] = {}
    weights_by_model: dict[str, dict[str, float]] = {}

    for embedding_path in embedding_paths:
        model_name = embedding_path.stem
        embeddings = np.load(embedding_path).astype(np.float32)
        if embeddings.shape[0] != len(rows):
            print(f"Skipping {model_name}: row count does not match catalogue")
            continue
        train_edges = same_type_training_edges(rows, component_split)

        def validation_score(matrix: np.ndarray, embedding_matrix=embeddings) -> float:
            engine = KindredEngine(rows, embedding_matrix, adapter=matrix)
            val_queries = _queries(primary, "val")
            rankings = _engine_rankings(engine, rows, val_queries)
            arrays = query_metric_arrays(rankings, [set(q.relevant) for q in val_queries], K)
            return float(arrays["ndcg@10"].mean()) if val_queries else 0.0

        adapter = train_adapter(
            embeddings, rows, train_edges, val_score=validation_score, seed=SEED
        )
        adapters[model_name] = adapter
        save_adapter(adapter, Path("results") / f"adapter_{model_name}.npz")
        weights, val_fusion_score = _choose_fusion(
            rows, embeddings, features, adapter, primary, percentiles
        )
        weights_by_model[model_name] = weights
        engines = _make_engines(rows, embeddings, features, adapter, weights)
        val = _evaluate_systems(rows, embeddings, features, primary, "val", engines, percentiles)
        validation_results[model_name] = val
        no_filter_results[model_name] = _evaluate_systems(
            rows, embeddings, features, no_filter, "val", engines, percentiles
        )
        model_data[model_name] = {
            "embedding": str(embedding_path),
            "shape": list(embeddings.shape),
            "adapter": {
                "temperature": adapter.temperature,
                "epochs": adapter.epochs,
                "output_dim": adapter.output_dim,
                "history": adapter.history,
            },
            "fusion_weights": weights,
            "val_fusion_ndcg@10": val_fusion_score,
        }
        if final:
            test_results[model_name] = _evaluate_systems(
                rows, embeddings, features, primary, "test", engines, percentiles
            )

    if not validation_results:
        raise RuntimeError("no embedding matched the catalogue")
    browser_models = [name for name in validation_results if name != "qwen3-0.6b"]
    chosen_model = max(
        browser_models or list(validation_results),
        key=lambda name: model_data[name]["val_fusion_ndcg@10"],
    )
    active = test_results if final else validation_results
    active_no_filter = (
        {name: _evaluate_systems(
            rows, np.load(Path(data["embedding"])), features, no_filter, "test",
            _make_engines(rows, np.load(Path(data["embedding"])), features, adapters[name], weights_by_model[name]),
            percentiles
        ) for name, data in model_data.items()}
        if final else no_filter_results
    )
    hypotheses = _hypotheses(active, active_no_filter, chosen_model)
    secondary_active = {}
    for name, data in model_data.items():
        embedding = np.load(Path(data["embedding"])).astype(np.float32)
        engines = _make_engines(rows, embedding, features, adapters[name], weights_by_model[name])
        secondary_active[name] = _evaluate_systems(
            rows, embedding, features, secondary, "test" if final else "val", engines, percentiles
        )

    serial_active = _json_summary(active)
    result = {
        "benchmark": "XM",
        "mode": "test" if final else "val",
        "seeds": {"split": SEED, "bootstrap": SEED, "random": SEED, "error_sample": SEED},
        "bootstrap_resamples": BOOTSTRAP,
        "counts": {"filtered": primary.counts, "no_component_filter": no_filter.counts,
                   "secondary": secondary.counts},
        "component_split_counts": {
            split: sum(value == split for value in component_split.values())
            for split in ("train", "val", "test")
        },
        "models": model_data,
        "results": serial_active,
        "direction_breakdown": _json_summary({
            name: _direction_breakdown(
                systems, _queries(primary, "test" if final else "val"), rows, percentiles
            ) for name, systems in active.items()
        }),
        "secondary_results": _json_summary(secondary_active),
        "hypotheses": _json_summary(hypotheses),
        "notes": [
            "Components are shuffled after sorting their string identifiers; train/val/test use floor(60%)/floor(10%)/remainder.",
            "Anime means anime and anime-film; print means manga, manhwa, manhua and novel.",
            "Fusion weights use a small validation-only grid over dense, tag TF-IDF and within-pool popularity z-score.",
            "Adapter output width is selected from 128 and 256 on validation; training uses AdamW, three validation temperatures and early stopping.",
            "Test output is produced only with --final; all model and fusion choices are made from validation results.",
            "Amendment after the first validation run (test untouched): the fusion grid gained a centering switch because centering did not help alone, two component ablations (fusion-no-pop, fusion-no-tag) were added, and the encoder is chosen by validation NDCG@10 of the full system instead of zero-shot.",
        ],
    }
    output_dir = Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "xm.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    table_lines = ["# XM ablation", "", f"Mode: {'test' if final else 'validation'}", ""]
    for model_name, systems in active.items():
        table_lines.extend([f"## {model_name}", "", _headline_table(systems), ""])
        table_lines.append("Popularity top-decile share (system vs ground truth):")
        ground_truth = systems["ground_truth"]["top_decile_share@10"]
        table_lines.append(f"ground truth: {ground_truth:.4f}")
        for system, value in systems.items():
            if system != "ground_truth":
                table_lines.append(f"{system}: {value['summary']['popularity_top_decile_share@10']:.4f}")
        table_lines.append("")
        direction = _direction_breakdown(
            systems, _queries(primary, "test" if final else "val"), rows, percentiles
        )
        if direction:
            dirs = sorted(direction)
            table_lines.extend(["NDCG@10 by direction (full detail in xm.json):", "",
                                "| System | " + " | ".join(dirs) + " |", "|---|" + "---:|" * len(dirs)])
            for system in direction[dirs[0]]:
                cells = [f"{direction[d][system]['ndcg@10']['mean']:.4f}" for d in dirs]
                table_lines.append(f"| {system} | " + " | ".join(cells) + " |")
            table_lines.append("")
    (output_dir / "xm_ablation.md").write_text("\n".join(table_lines), encoding="utf-8")

    if final:
        selected_systems = test_results[chosen_model]
        embedding = np.load(Path(model_data[chosen_model]["embedding"])).astype(np.float32)
        _write_errors(
            output_dir / "xm_errors.md", rows, _queries(primary, "test"),
            selected_systems["fusion"]["rankings"]
        )
        print("Test headline:")
        print(_headline_table(selected_systems))
        print("Hypotheses:", json.dumps(hypotheses["supported"], sort_keys=True))
    else:
        print("Validation headline:")
        print(_headline_table(validation_results[chosen_model]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="score test once using validation choices")
    args = parser.parse_args()
    run(final=args.final)


if __name__ == "__main__":
    main()
