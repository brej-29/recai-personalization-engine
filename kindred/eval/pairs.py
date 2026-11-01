"""Construction of the XM query sets and leakage-safe training edges."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PRINT_MEDIA = {"manga", "manhwa", "manhua", "novel"}
ANIME_MEDIA = {"anime", "anime-film"}


@dataclass(frozen=True)
class Query:
    query_idx: int
    relevant: tuple[int, ...]
    candidates: tuple[int, ...]
    direction: str
    split: str


@dataclass
class PairSet:
    queries: list[Query]
    pairs: list[tuple[int, int]]
    counts: dict[str, object]


def load_catalog(path: str | Path = "data/catalog.jsonl") -> list[dict]:
    """Load catalogue rows without changing their order."""
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _type_of(row: dict) -> str | None:
    if row.get("medium") in ANIME_MEDIA:
        return "anime"
    if row.get("medium") in PRINT_MEDIA:
        return "print"
    return None


def split_components(rows: list[dict], seed: int = 13) -> dict[str, str]:
    """Assign every catalogue component to train/val/test once, deterministically."""
    components = sorted({str(row.get("comp", row["id"])) for row in rows})
    rng = np.random.default_rng(seed)
    order = rng.permutation(components)
    n_train = int(len(order) * 0.60)
    n_val = int(len(order) * 0.10)
    assignment = {}
    for component in order[:n_train]:
        assignment[str(component)] = "train"
    for component in order[n_train:n_train + n_val]:
        assignment[str(component)] = "val"
    for component in order[n_train + n_val:]:
        assignment[str(component)] = "test"
    return assignment


def _adaptation_targets(rows: list[dict]) -> dict[int, set[int]]:
    by_aid = {row.get("_aid"): i for i, row in enumerate(rows) if row.get("_aid") is not None}
    targets: dict[int, set[int]] = defaultdict(set)
    for i, row in enumerate(rows):
        source_type = _type_of(row)
        if source_type is None:
            continue
        for target_aid, relation in row.get("_relt", []):
            if relation not in {"ADAPTATION", "SOURCE"}:
                continue
            target_idx = by_aid.get(target_aid)
            if target_idx is None or _type_of(rows[target_idx]) == source_type:
                continue
            targets[i].add(target_idx)
    return targets


def _recommendation_edges(rows: list[dict]) -> list[tuple[int, int]]:
    by_aid = {row.get("_aid"): i for i, row in enumerate(rows) if row.get("_aid") is not None}
    edges: set[tuple[int, int]] = set()
    for i, row in enumerate(rows):
        source_type = _type_of(row)
        if source_type is None:
            continue
        for target_aid, rating in row.get("_rec", []):
            target_idx = by_aid.get(target_aid)
            if target_idx is None or rating < 2 or _type_of(rows[target_idx]) != source_type:
                continue
            if i != target_idx:
                edges.add(tuple(sorted((i, target_idx))))
    return sorted(edges)


def _candidate_pool(
    rows: list[dict], query_idx: int, filter_components: bool, allowed_types: set[str] | None = None
) -> tuple[int, ...]:
    query_type = _type_of(rows[query_idx])
    if query_type is None:
        return ()
    other = "print" if query_type == "anime" else "anime"
    query_comp = rows[query_idx].get("comp", rows[query_idx]["id"])
    return tuple(
        i for i, row in enumerate(rows)
        if _type_of(row) == other
        and (allowed_types is None or row.get("medium") in allowed_types)
        and (not filter_components or row.get("comp", row["id"]) != query_comp)
    )


def _group_pairs(
    rows: list[dict],
    pairs: Iterable[tuple[int, int]],
    component_split: dict[str, str],
    filter_components: bool,
    allowed_target_media: set[str] | None = None,
) -> PairSet:
    grouped: dict[tuple[int, str], set[int]] = defaultdict(set)
    kept_pairs: set[tuple[int, int]] = set()
    for query_idx, target_idx in pairs:
        query_type = _type_of(rows[query_idx])
        target_type = _type_of(rows[target_idx])
        if query_type is None or target_type is None or query_type == target_type:
            continue
        query_comp = rows[query_idx].get("comp", rows[query_idx]["id"])
        target_comp = rows[target_idx].get("comp", rows[target_idx]["id"])
        if filter_components and query_comp == target_comp:
            continue
        split = component_split[str(query_comp)]
        if allowed_target_media is not None and rows[target_idx].get("medium") not in allowed_target_media:
            continue
        grouped[(query_idx, split)].add(target_idx)
        kept_pairs.add((query_idx, target_idx))

    queries = []
    for (query_idx, split), relevant in sorted(grouped.items()):
        candidate_pool = _candidate_pool(
            rows, query_idx, filter_components, allowed_types=allowed_target_media
        )
        relevant = relevant.intersection(candidate_pool)
        if not relevant or not candidate_pool:
            continue
        queries.append(
            Query(
                query_idx=query_idx,
                relevant=tuple(sorted(relevant)),
                candidates=candidate_pool,
                direction=f"{_type_of(rows[query_idx])}->{_type_of(rows[next(iter(relevant))])}",
                split=split,
            )
        )

    counts: dict[str, object] = {
        "queries": len(queries),
        "pairs": sum(len(query.relevant) for query in queries),
        "by_split": {},
        "by_direction": {},
    }
    for split in ("train", "val", "test"):
        split_queries = [query for query in queries if query.split == split]
        counts["by_split"][split] = {
            "queries": len(split_queries),
            "pairs": sum(len(query.relevant) for query in split_queries),
            "pool_sizes": sorted({len(query.candidates) for query in split_queries}),
        }
    for direction in ("anime->print", "print->anime"):
        direction_queries = [query for query in queries if query.direction == direction]
        counts["by_direction"][direction] = {
            "queries": len(direction_queries),
            "pairs": sum(len(query.relevant) for query in direction_queries),
            "pool_sizes": sorted({len(query.candidates) for query in direction_queries}),
        }
    return PairSet(queries=queries, pairs=sorted(kept_pairs), counts=counts)


def build_xm_pairs(
    rows: list[dict], seed: int = 13, filter_components: bool = True
) -> tuple[PairSet, dict[str, str]]:
    """Build the adaptation-bridged XM pairs and their component split."""
    component_split = split_components(rows, seed)
    adaptation_targets = _adaptation_targets(rows)
    recommendations = _recommendation_edges(rows)
    pairs = []
    for left, right in recommendations:
        for query_idx, neighbour_idx in ((left, right), (right, left)):
            for target_idx in adaptation_targets.get(neighbour_idx, set()):
                if _type_of(rows[target_idx]) != ("print" if _type_of(rows[query_idx]) == "anime" else "anime"):
                    continue
                pairs.append((query_idx, target_idx))
    return _group_pairs(rows, pairs, component_split, filter_components), component_split


def build_secondary_pairs(
    rows: list[dict], component_split: dict[str, str], filter_components: bool = True
) -> PairSet:
    """Build direct recommendation edges between manga, manhwa and manhua."""
    edges = _recommendation_edges(rows)
    pairs = []
    for left, right in edges:
        if rows[left].get("medium") not in {"manga", "manhwa", "manhua"}:
            continue
        if rows[right].get("medium") not in {"manga", "manhwa", "manhua"}:
            continue
        if rows[left].get("medium") == rows[right].get("medium"):
            continue
        pairs.extend(((left, right), (right, left)))
    grouped: dict[tuple[int, str], set[int]] = defaultdict(set)
    kept_pairs: set[tuple[int, int]] = set()
    allowed = {"manga", "manhwa", "manhua"}
    for query_idx, target_idx in pairs:
        if rows[query_idx].get("medium") not in allowed or rows[target_idx].get("medium") not in allowed:
            continue
        if rows[query_idx].get("medium") == rows[target_idx].get("medium"):
            continue
        query_comp = rows[query_idx].get("comp", rows[query_idx]["id"])
        target_comp = rows[target_idx].get("comp", rows[target_idx]["id"])
        if filter_components and query_comp == target_comp:
            continue
        split = component_split[str(query_comp)]
        grouped[(query_idx, split)].add(target_idx)
        kept_pairs.add((query_idx, target_idx))

    queries = []
    for (query_idx, split), relevant in sorted(grouped.items()):
        query_medium = rows[query_idx].get("medium")
        query_comp = rows[query_idx].get("comp", rows[query_idx]["id"])
        candidates = tuple(
            i for i, row in enumerate(rows)
            if row.get("medium") in allowed
            and row.get("medium") != query_medium
            and (not filter_components or row.get("comp", row["id"]) != query_comp)
        )
        relevant = relevant.intersection(candidates)
        if not relevant or not candidates:
            continue
        queries.append(
            Query(query_idx, tuple(sorted(relevant)), candidates,
                  f"{query_medium}->{rows[next(iter(relevant))].get('medium')}", split)
        )
    counts: dict[str, object] = {
        "queries": len(queries),
        "pairs": sum(len(query.relevant) for query in queries),
        "by_split": {},
        "by_direction": {},
    }
    for split in ("train", "val", "test"):
        split_queries = [query for query in queries if query.split == split]
        counts["by_split"][split] = {
            "queries": len(split_queries),
            "pairs": sum(len(query.relevant) for query in split_queries),
            "pool_sizes": sorted({len(query.candidates) for query in split_queries}),
        }
    for direction in sorted({query.direction for query in queries}):
        direction_queries = [query for query in queries if query.direction == direction]
        counts["by_direction"][direction] = {
            "queries": len(direction_queries),
            "pairs": sum(len(query.relevant) for query in direction_queries),
            "pool_sizes": sorted({len(query.candidates) for query in direction_queries}),
        }
    return PairSet(queries, sorted(kept_pairs), counts)


def same_type_training_edges(
    rows: list[dict], component_split: dict[str, str]
) -> list[tuple[int, int]]:
    """Return recommendation edges left after the preregistered leakage removal."""
    edges = _recommendation_edges(rows)
    held_out = {i for i, row in enumerate(rows) if component_split[str(row.get("comp", row["id"]))] != "train"}
    return [(left, right) for left, right in edges if left not in held_out and right not in held_out]
