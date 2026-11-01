"""MovieLens cold-start benchmark for content and collaborative recommenders."""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from kindred.eval.metrics import (
    bootstrap_mean_ci,
    paired_bootstrap,
    query_metric_arrays,
)

try:
    from kindred.engine import KindredEngine, family_center
except ImportError:  # pragma: no cover - the normal package includes the engine
    KindredEngine = None
    family_center = None


K_VALUES = (1, 3, 5, 10)
MODEL_NAMES = ("minilm", "bge-small", "gte-small", "qwen3-0.6b")
SEEDS = {
    "user_sample": 13,
    "user_split": 17,
    "seed_ratings": 19,
    "random_rankings": 23,
    "hybrid_validation": 29,
    "bootstrap": 31,
}


def imdb_catalog_id(imdb_id: str | int) -> str:
    """Return the catalogue ID used for a MovieLens IMDb identifier."""
    value = str(imdb_id).strip()
    return f"im:{'tt' + value.zfill(7)}"


def join_catalogue_movies(
    rows: list[dict], links: Iterable[dict[str, str]]
) -> list[tuple[int, int]]:
    """Join catalogue movie rows to MovieLens movie IDs using IMDb IDs."""
    by_id = {row.get("id"): index for index, row in enumerate(rows) if row.get("medium") == "movie"}
    joined = []
    for link in links:
        imdb_id = link.get("imdbId", "")
        movie_id = link.get("movieId", "")
        if not imdb_id or not movie_id:
            continue
        catalog_index = by_id.get(imdb_catalog_id(imdb_id))
        if catalog_index is not None:
            joined.append((int(movie_id), catalog_index))
    return joined


def seed_holdout(
    liked_movies: Iterable[int], k: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Choose k random liked movies and return seeds plus the held-out items."""
    liked = np.asarray(list(liked_movies), dtype=int)
    if k < 1 or k >= liked.size:
        raise ValueError("k must leave at least one held-out liked movie")
    order = rng.permutation(liked.size)
    seeds = liked[order[:k]]
    held_out = liked[order[k:]]
    return seeds, held_out


def item_knn_similarity(user_item: np.ndarray) -> np.ndarray:
    """Build cosine item similarity from a user by item rating matrix."""
    matrix = np.asarray(user_item, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("user_item must be a two-dimensional matrix")
    norms = np.linalg.norm(matrix, axis=0)
    gram = matrix.T @ matrix
    denominator = np.outer(norms, norms)
    return np.divide(gram, denominator, out=np.zeros_like(gram), where=denominator > 0)


def _sparse_item_knn_similarity(user_item: object) -> object:
    """Build cosine item similarity while retaining sparse structure when scipy exists."""
    try:
        from scipy import sparse
    except ImportError:
        dense = user_item.toarray() if hasattr(user_item, "toarray") else user_item
        return item_knn_similarity(np.asarray(dense))
    matrix = sparse.csr_matrix(user_item, dtype=np.float32)
    norms = np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=0)).ravel())
    inverse = np.divide(1.0, norms, out=np.zeros_like(norms), where=norms > 0)
    similarity = (matrix.T @ matrix).tocsr()
    similarity = similarity.multiply(inverse[:, None]).multiply(inverse[None, :])
    return similarity.tocsr()


def rank_item_knn(
    similarity: object,
    seeds: Iterable[int],
    candidates: Iterable[int],
    popularity: np.ndarray | None = None,
    popularity_weight: float = 0.0,
) -> np.ndarray:
    """Rank candidates by summed seed similarity and optional popularity weight."""
    seeds = np.asarray(list(seeds), dtype=int)
    candidates = np.asarray(list(candidates), dtype=int)
    if not candidates.size:
        return candidates
    if hasattr(similarity, "__getitem__") and not isinstance(similarity, np.ndarray):
        scores = np.asarray(similarity[seeds].sum(axis=0)).ravel()[candidates]
    else:
        scores = np.asarray(similarity)[np.ix_(seeds, candidates)].sum(axis=0)
    if popularity_weight and popularity is not None:
        pop = np.asarray(popularity, dtype=float)
        pop = (pop - pop.mean()) / max(float(pop.std()), 1e-12)
        scores = scores + popularity_weight * pop[candidates]
    order = np.argsort(-scores, kind="mergesort")
    return candidates[order]


def crossover_k(
    by_k: dict[int, tuple[np.ndarray, np.ndarray]],
    n_resamples: int = 10_000,
    seed: int = SEEDS["bootstrap"],
) -> tuple[int | None, dict[str, object]]:
    """Find the first k where CF beats content with a separated paired CI."""
    evidence: dict[str, object] = {}
    for k in sorted(by_k):
        cf_values, content_values = by_k[k]
        result = paired_bootstrap(
            np.asarray(cf_values),
            np.asarray(content_values),
            n_resamples=n_resamples,
            seed=seed + int(k),
        )
        evidence[str(k)] = result
        if result["mean_diff"] > 0 and result["ci_low"] > 0:
            return k, evidence
    return None, evidence


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _ensure_ml_root(raw_dir: Path) -> Path:
    target = raw_dir / "ml-25m"
    if (target / "links.csv").exists() and (target / "ratings.csv").exists():
        return target
    archive = raw_dir / "ml-25m.zip"
    if not archive.exists():
        raise FileNotFoundError(f"MovieLens archive not found: {archive}")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        source.extractall(raw_dir)
    if not (target / "links.csv").exists():
        raise FileNotFoundError(f"MovieLens files were not found under {target}")
    return target


def _read_links(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _ratings_path(root: Path) -> Path:
    return root / "ratings.csv"


def _scan_likes(
    path: Path,
    movie_to_local: dict[int, int],
) -> tuple[dict[int, list[int]], int]:
    liked: dict[int, list[int]] = defaultdict(list)
    catalogue_ratings = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            movie_id = int(row["movieId"])
            local = movie_to_local.get(movie_id)
            if local is None:
                continue
            catalogue_ratings += 1
            if float(row["rating"]) >= 4.0:
                liked[int(row["userId"])].append(local)
    return liked, catalogue_ratings


def _read_selected_ratings(
    path: Path,
    movie_to_local: dict[int, int],
    selected_users: set[int],
) -> dict[int, list[tuple[int, float]]]:
    ratings = {user: [] for user in selected_users}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            user = int(row["userId"])
            if user not in selected_users:
                continue
            local = movie_to_local.get(int(row["movieId"]))
            if local is not None:
                ratings[user].append((local, float(row["rating"])))
    return ratings


def _make_user_item(
    user_ids: list[int], ratings: dict[int, list[tuple[int, float]]], n_items: int
) -> tuple[object, np.ndarray]:
    try:
        from scipy import sparse
    except ImportError:
        matrix = np.zeros((len(user_ids), n_items), dtype=np.float32)
        for row_index, user in enumerate(user_ids):
            for item, rating in ratings[user]:
                matrix[row_index, item] = rating
        return matrix, np.asarray(matrix.sum(axis=0)).ravel()
    values = []
    row_indices = []
    col_indices = []
    for row_index, user in enumerate(user_ids):
        for item, rating in ratings[user]:
            row_indices.append(row_index)
            col_indices.append(item)
            values.append(rating)
    matrix = sparse.csr_matrix(
        (values, (row_indices, col_indices)), shape=(len(user_ids), n_items), dtype=np.float32
    )
    return matrix, np.asarray(matrix.sum(axis=0)).ravel()


def _normalise_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def _top_scores(scores: np.ndarray, candidates: np.ndarray, limit: int = 10) -> np.ndarray:
    order = np.argsort(-np.asarray(scores), kind="mergesort")
    return candidates[order[:limit]]


def _genre_scores(rows: list[dict], seeds: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    seed_genres = [set(rows[int(index)].get("genres", [])) for index in seeds]
    result = np.zeros(candidates.size, dtype=np.float32)
    for position, candidate in enumerate(candidates):
        candidate_genres = set(rows[int(candidate)].get("genres", []))
        values = []
        for genres in seed_genres:
            union = genres | candidate_genres
            values.append(len(genres & candidate_genres) / len(union) if union else 0.0)
        result[position] = float(np.mean(values)) if values else 0.0
    return result


def _mean_metric(metrics: dict[str, np.ndarray], name: str) -> float:
    values = metrics.get(name, np.zeros(0))
    return float(np.mean(values)) if values.size else 0.0


def _metric_summary(
    rankings: list[np.ndarray], relevant: list[set[int]], seed: int, n_resamples: int
) -> dict[str, dict[str, float]]:
    if not rankings:
        empty = {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
        return {name: dict(empty) for name in ("ndcg@10", "recall@10", "mrr", "hit@10")}
    arrays = query_metric_arrays(rankings, relevant)
    return {
        name: bootstrap_mean_ci(values, n_resamples=n_resamples, seed=seed + offset)
        for offset, (name, values) in enumerate(arrays.items())
    }


def _write_markdown(result: dict, path: Path) -> None:
    lines = [
        "# MovieLens 25M benchmark",
        "",
        "This is a live-action cold-start sanity check. Scores are means with paired query bootstrap 95% CIs.",
        "",
        "## Counts",
        "",
    ]
    for key, value in result["counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Protocol", ""])
    for key, value in result["protocol"].items():
        lines.append(f"- {key}: {value}")
    for k in K_VALUES:
        block = result["results"][str(k)]
        lines.extend(
            [
                "",
                f"## k = {k}",
                "",
                "| System | NDCG@10 | Recall@10 | MRR | Hit@10 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for system, metrics in block["metrics"].items():
            cells = []
            for metric in ("ndcg@10", "recall@10", "mrr", "hit@10"):
                value = metrics[metric]
                cells.append(f"{value['mean']:.4f} [{value['ci_low']:.4f}, {value['ci_high']:.4f}]")
            lines.append(f"| {system} | " + " | ".join(cells) + " |")
        lines.extend(
            [
                "",
                "Popularity-filtered variant: users whose held-out items are not all in the train global top-100.",
                "",
                "| System | NDCG@10 | Recall@10 |",
                "|---|---:|---:|",
            ]
        )
        for system, metrics in block["variant_metrics"].items():
            lines.append(
                f"| {system} | {metrics['ndcg@10']['mean']:.4f} [{metrics['ndcg@10']['ci_low']:.4f}, {metrics['ndcg@10']['ci_high']:.4f}] | "
                f"{metrics['recall@10']['mean']:.4f} [{metrics['recall@10']['ci_low']:.4f}, {metrics['recall@10']['ci_high']:.4f}] |"
            )
        lines.append(
            f"\nHybrid source: {block['hybrid']['source']}; validation weight on item-kNN: {block['hybrid']['item_knn_weight']:.2f}."
        )
    lines.extend(
        [
            "",
            "## Crossover",
            "",
            f"Smallest k with item-kNN NDCG@10 above the best content system with a separated paired CI: **{result['crossover']['k'] or 'none observed'}**.",
            "",
            "## H6",
            "",
            result["h6"]["verdict"],
        ]
    )
    if result["notes"]:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in result["notes"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_benchmark(
    data_dir: str | Path = "data",
    results_dir: str | Path = "results",
    sample_users: int = 5_000,
    n_resamples: int = 10_000,
) -> dict:
    """Run the registered MovieLens benchmark and write JSON plus Markdown."""
    data_dir = Path(data_dir)
    results_dir = Path(results_dir)
    rows = _load_rows(data_dir / "catalog.jsonl")
    ml_root = _ensure_ml_root(data_dir / "raw")
    joined = join_catalogue_movies(rows, _read_links(ml_root / "links.csv"))
    if not joined:
        raise RuntimeError("No catalogue movies joined to MovieLens")
    movie_ids = np.asarray([catalog_index for _, catalog_index in joined], dtype=int)
    ml_movie_ids = [movie_id for movie_id, _ in joined]
    movie_to_local = {movie_id: local for local, movie_id in enumerate(ml_movie_ids)}
    local_rows = [rows[int(index)] for index in movie_ids]
    n_movies = len(local_rows)

    liked_by_user, catalogue_ratings = _scan_likes(_ratings_path(ml_root), movie_to_local)
    eligible = sorted(user for user, liked in liked_by_user.items() if len(set(liked)) >= 20)
    rng = np.random.default_rng(SEEDS["user_sample"])
    if len(eligible) > sample_users:
        sampled_users = sorted(rng.choice(eligible, size=sample_users, replace=False).tolist())
    else:
        sampled_users = eligible
    split_rng = np.random.default_rng(SEEDS["user_split"])
    split_order = split_rng.permutation(sampled_users)
    n_train = int(len(split_order) * 0.8)
    train_users = [int(user) for user in split_order[:n_train]]
    test_users = [int(user) for user in split_order[n_train:]]
    n_val = max(1, int(len(test_users) * 0.2)) if test_users else 0
    val_users = test_users[:n_val]
    eval_users = test_users[n_val:]
    selected_ratings = _read_selected_ratings(
        _ratings_path(ml_root), movie_to_local, set(sampled_users)
    )
    train_matrix, train_counts = _make_user_item(train_users, selected_ratings, n_movies)
    similarity = _sparse_item_knn_similarity(train_matrix)
    popularity = np.asarray(train_counts, dtype=float)
    top100 = set(np.argsort(-popularity, kind="mergesort")[: min(100, n_movies)].tolist())
    pop_score = np.log1p(popularity)

    emb_dir = data_dir / "emb"
    embeddings: dict[str, np.ndarray] = {}
    for model in MODEL_NAMES:
        path = emb_dir / f"{model}.npy"
        if path.exists():
            matrix = np.load(path, mmap_mode="r")
            if matrix.shape[0] == len(rows):
                embeddings[model] = _normalise_rows(np.asarray(matrix[movie_ids]))
    if not embeddings:
        raise RuntimeError("No aligned movie embedding was found")

    notes = [
        "ALS was skipped because the optional implicit package is not installed.",
        "Item-kNN uses the 80 percent train-user rating matrix; popularity is train rating count.",
        "The hybrid weight is selected from the first 20 percent of held-out test users and then fixed for evaluation users.",
    ]
    centered_embeddings: dict[str, np.ndarray] = {}
    for model, dense in embeddings.items():
        full_matrix = np.asarray(np.load(emb_dir / f"{model}.npy", mmap_mode="r"), dtype=np.float32)
        if KindredEngine is not None and family_center is not None:
            centered_full = KindredEngine(rows, full_matrix, centered=True).embeddings
            centered_embeddings[model] = _normalise_rows(centered_full[movie_ids])
        else:  # pragma: no cover - kept for environments missing the engine module
            centered_embeddings[model] = _normalise_rows(family_center(dense, ["live"] * n_movies))

    adapter_embeddings: dict[str, np.ndarray] = {}
    adapter_paths: dict[str, str] = {}
    for model in embeddings:
        dense = centered_embeddings[model]
        adapter_path = results_dir / f"adapter_{model}.npz"
        if not adapter_path.exists():
            continue
        with np.load(adapter_path) as archive:
            if "W" in archive:
                matrix = np.asarray(archive["W"])
            else:
                keys = list(archive.files)
                matrix = np.asarray(archive[keys[0]]) if keys else None
        if matrix is None or matrix.ndim != 2 or matrix.shape[0] != dense.shape[1]:
            notes.append(
                f"Adapter for {model} was skipped because its matrix shape is incompatible."
            )
            continue
        adapter_embeddings[model] = _normalise_rows(dense @ matrix)
        adapter_paths[model] = str(adapter_path)
    for model in embeddings:
        if model not in adapter_embeddings:
            notes.append(
                f"No usable adapter file found for {model}; its adapter system was skipped."
            )

    kindred_model = "minilm" if "minilm" in centered_embeddings else next(iter(centered_embeddings))
    centered = centered_embeddings[kindred_model]
    embeddings["Kindred"] = centered
    content_names = [f"Dense:{model}" for model in embeddings if model != "Kindred"]
    content_names.append("Kindred")
    for model in adapter_embeddings:
        content_names.append(f"Kindred+adapter:{model}")
    base_systems = ["Random", "Popularity", "Genre", "Item-kNN", "Item-kNN+pop"] + content_names

    def user_seed(user: int, k: int) -> tuple[np.ndarray, np.ndarray]:
        liked = np.asarray(sorted(set(liked_by_user[user])), dtype=int)
        local_rng = np.random.default_rng(SEEDS["seed_ratings"] + user * 1009 + k * 9176)
        return seed_holdout(liked, k, local_rng)

    def get_scores(system: str, seeds: np.ndarray, candidates: np.ndarray) -> np.ndarray | None:
        if system == "Popularity":
            return pop_score[candidates]
        if system == "Genre":
            return _genre_scores(local_rows, seeds, candidates)
        if system == "Item-kNN":
            return np.asarray(similarity[seeds].sum(axis=0)).ravel()[candidates]
        if system == "Item-kNN+pop":
            return np.asarray(rank_item_knn(similarity, seeds, candidates, popularity, 0.15))
        if system.startswith("Dense:"):
            matrix = embeddings[system.split(":", 1)[1]]
        elif system == "Kindred":
            matrix = embeddings["Kindred"]
        elif system.startswith("Kindred+adapter:"):
            matrix = adapter_embeddings[system.split(":", 1)[1]]
        else:
            return None
        query = np.mean(matrix[seeds], axis=0)
        query /= max(float(np.linalg.norm(query)), 1e-12)
        return matrix[candidates] @ query

    def collect(
        users: list[int], k: int, systems: list[str]
    ) -> tuple[dict, list[set[int]], list[dict]]:
        rankings = {system: [] for system in systems}
        relevant = []
        records = []
        candidates_all = np.arange(n_movies, dtype=int)
        for user in users:
            seeds, held_out = user_seed(user, k)
            candidates = candidates_all[~np.isin(candidates_all, seeds)]
            relevant.append({int(item) for item in held_out})
            record = {"candidates": candidates, "seeds": seeds, "relevant": held_out, "scores": {}}
            for system in systems:
                scores = get_scores(system, seeds, candidates)
                if scores is None:
                    random_rng = np.random.default_rng(
                        SEEDS["random_rankings"] + user * 1009 + k * 9176
                    )
                    ranking = random_rng.permutation(candidates)[:10]
                elif system == "Item-kNN+pop":
                    ranking = rank_item_knn(similarity, seeds, candidates, popularity, 0.15)[:10]
                else:
                    record["scores"][system] = np.asarray(scores)
                    ranking = _top_scores(scores, candidates)
                rankings[system].append(ranking)
            records.append(record)
        return rankings, relevant, records

    all_results: dict[str, dict] = {}
    crossover_inputs: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    h6_inputs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for k in K_VALUES:
        val_rankings, val_relevant, val_records = collect(val_users, k, base_systems)
        val_metric_arrays = {
            name: query_metric_arrays(values, val_relevant) for name, values in val_rankings.items()
        }
        content_scores = {
            system: _mean_metric(val_metric_arrays[system], "ndcg@10") for system in content_names
        }
        best_content = (
            max(content_scores, key=content_scores.get) if content_scores else "Dense:minilm"
        )
        weights = np.linspace(0.0, 1.0, 5)
        best_weight = 0.5
        best_score = -np.inf
        for weight in weights:
            hybrid_rankings = []
            for record in val_records:
                candidates = record["candidates"]
                cf_scores = record["scores"].get("Item-kNN")
                dense_scores = record["scores"].get(best_content)
                if cf_scores is None or dense_scores is None:
                    continue
                cf_min, cf_max = float(cf_scores.min()), float(cf_scores.max())
                de_min, de_max = float(dense_scores.min()), float(dense_scores.max())
                cf_norm = (cf_scores - cf_min) / max(cf_max - cf_min, 1e-12)
                de_norm = (dense_scores - de_min) / max(de_max - de_min, 1e-12)
                hybrid_rankings.append(
                    _top_scores(weight * cf_norm + (1 - weight) * de_norm, candidates)
                )
            score = _mean_metric(query_metric_arrays(hybrid_rankings, val_relevant), "ndcg@10")
            if score > best_score:
                best_score, best_weight = score, float(weight)

        eval_systems = base_systems
        rankings, relevant, records = collect(eval_users, k, eval_systems)
        rankings["Hybrid"] = []
        for record in records:
            candidates = record["candidates"]
            cf_scores = record["scores"].get("Item-kNN")
            dense_scores = record["scores"].get(best_content)
            if cf_scores is None or dense_scores is None:
                rankings["Hybrid"].append(candidates[:10])
                continue
            cf_norm = (cf_scores - cf_scores.min()) / max(
                float(cf_scores.max() - cf_scores.min()), 1e-12
            )
            de_norm = (dense_scores - dense_scores.min()) / max(
                float(dense_scores.max() - dense_scores.min()), 1e-12
            )
            rankings["Hybrid"].append(
                _top_scores(best_weight * cf_norm + (1 - best_weight) * de_norm, candidates)
            )
        metrics = {
            system: _metric_summary(values, relevant, SEEDS["bootstrap"] + k * 100, n_resamples)
            for system, values in rankings.items()
        }
        variant_mask = np.asarray(
            [not {int(item) for item in rel}.issubset(top100) for rel in relevant], dtype=bool
        )
        variant_metrics = {
            system: _metric_summary(
                [ranking for ranking, keep in zip(values, variant_mask) if keep],
                [rel for rel, keep in zip(relevant, variant_mask) if keep],
                SEEDS["bootstrap"] + k * 100 + 50,
                n_resamples,
            )
            for system, values in rankings.items()
        }
        content_eval_arrays = {
            system: query_metric_arrays(rankings[system], relevant) for system in content_names
        }
        crossover_inputs[k] = (
            query_metric_arrays(rankings["Item-kNN"], relevant)["ndcg@10"],
            content_eval_arrays[best_content]["ndcg@10"],
        )
        for model in adapter_embeddings:
            adapter_name = f"Kindred+adapter:{model}"
            zero_name = f"Dense:{model}"
            if zero_name in rankings:
                h6_inputs.setdefault(adapter_name, ([], []))
                h6_inputs[adapter_name][0].extend(
                    query_metric_arrays(rankings[adapter_name], relevant)["recall@10"]
                )
                h6_inputs[adapter_name][1].extend(
                    query_metric_arrays(rankings[zero_name], relevant)["recall@10"]
                )
        all_results[str(k)] = {
            "metrics": metrics,
            "variant_metrics": variant_metrics,
            "variant_users": int(variant_mask.sum()),
            "best_content": best_content,
            "hybrid": {"source": best_content, "item_knn_weight": best_weight},
        }

    cross_k, cross_evidence = crossover_k(crossover_inputs, n_resamples=n_resamples)
    if h6_inputs:
        h6_comparisons = {}
        for name, (adapter_values, zero_values) in h6_inputs.items():
            h6_comparisons[name] = paired_bootstrap(
                np.asarray(adapter_values),
                np.asarray(zero_values),
                n_resamples=n_resamples,
                seed=SEEDS["bootstrap"],
            )
        supported = any(value["ci_low"] > 0 for value in h6_comparisons.values())
        verdict = (
            "H6 supported: at least one adapter has a positive, CI-separated Recall@10 gain over its zero-shot model."
            if supported
            else "H6 not supported: no adapter has a positive, CI-separated Recall@10 gain over its zero-shot model."
        )
    else:
        h6_comparisons = {}
        verdict = "H6 not testable: no usable adapter file was present."

    result = {
        "benchmark": "MovieLens 25M live-action sanity check",
        "seeds": SEEDS,
        "counts": {
            "catalogue_rows": len(rows),
            "catalogue_movie_rows": int(sum(row.get("medium") == "movie" for row in rows)),
            "catalogue_movies_with_movielens_link": n_movies,
            "catalogue_ratings": catalogue_ratings,
            "eligible_users": len(eligible),
            "sampled_users": len(sampled_users),
            "train_users": len(train_users),
            "validation_users": len(val_users),
            "test_users": len(test_users),
            "evaluated_users": len(eval_users),
            "train_ratings": int(
                train_matrix.nnz if hasattr(train_matrix, "nnz") else np.count_nonzero(train_matrix)
            ),
        },
        "protocol": {
            "eligibility": "at least 20 catalogue movie ratings at 4 stars or higher",
            "seed_values": list(K_VALUES),
            "candidate_pool": "all linked catalogue movies except seeds",
            "cf_split": "80 percent train users, 20 percent test users; validation is first 20 percent of test users",
            "bootstrap": f"paired query bootstrap, {n_resamples} resamples, 95 percent CI",
            "popularity_filter": "held-out items not all in train global top-100",
        },
        "systems": base_systems + ["Hybrid"],
        "results": all_results,
        "crossover": {"k": cross_k, "paired_ndcg_diff": cross_evidence},
        "h6": {"verdict": verdict, "comparisons": h6_comparisons, "adapter_files": adapter_paths},
        "notes": notes,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "ml.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(result, results_dir / "ml.md")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--sample-users", type=int, default=5_000)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    args = parser.parse_args()
    run_benchmark(args.data_dir, args.results_dir, args.sample_users, args.bootstrap)


if __name__ == "__main__":
    main()
