import numpy as np

from kindred.engine import KindredEngine, family_center
from kindred.eval.metrics import mrr, ndcg_at_k, paired_bootstrap
from kindred.eval.pairs import build_xm_pairs, split_components


def test_hand_computed_ranking_metrics():
    assert np.isclose(ndcg_at_k([2, 0, 3], {2, 3}, 3),
                      (1 + 1 / np.log2(4)) / (1 + 1 / np.log2(3)))
    assert mrr([0, 3, 2], {3}, 10) == 0.5


def test_bootstrap_is_paired_and_deterministic():
    first = np.asarray([1.0, 0.0, 1.0, 0.0])
    second = np.zeros(4)
    left = paired_bootstrap(first, second, n_resamples=500, seed=13)
    right = paired_bootstrap(first, second, n_resamples=500, seed=13)
    assert left == right
    assert left["mean_diff"] == 0.5
    assert left["ci_low"] <= 0.5 <= left["ci_high"]


def _leakage_rows():
    return [
        {"id": "al:1", "_aid": 1, "medium": "anime", "family": "anime",
         "comp": "c0", "_rec": [[2, 2]], "_relt": []},
        {"id": "al:2", "_aid": 2, "medium": "anime", "family": "anime",
         "comp": "c1", "_rec": [], "_relt": [[3, "ADAPTATION"]]},
        {"id": "al:3", "_aid": 3, "medium": "manga", "family": "print",
         "comp": "c0", "_rec": [], "_relt": []},
    ]


def test_component_filter_removes_leaky_target():
    rows = _leakage_rows()
    filtered, _ = build_xm_pairs(rows, seed=13, filter_components=True)
    unfiltered, _ = build_xm_pairs(rows, seed=13, filter_components=False)
    assert filtered.pairs == []
    assert unfiltered.pairs == [(0, 2)]


def test_component_split_is_deterministic():
    rows = [{"id": str(i), "comp": f"c{i}"} for i in range(20)]
    assert split_components(rows, 13) == split_components(rows, 13)
    result = split_components(rows, 13)
    assert sum(value == "train" for value in result.values()) == 12
    assert sum(value == "val" for value in result.values()) == 2


def test_family_centering_subtracts_family_mean_and_normalizes():
    matrix = np.asarray([[1, 0], [3, 0], [0, 1]], dtype=np.float32)
    centered = family_center(matrix, ["a", "a", "b"])
    assert np.allclose(centered[0], [-1, 0])
    assert np.allclose(centered[1], [1, 0])
    assert np.allclose(centered[2], [0, 0])


def test_engine_averages_seeds_and_filters_medium():
    rows = [
        {"family": "anime", "medium": "anime", "pop": 1},
        {"family": "anime", "medium": "anime", "pop": 1},
        {"family": "print", "medium": "manga", "pop": 1},
        {"family": "anime", "medium": "anime-film", "pop": 1},
    ]
    embeddings = np.asarray([[1, 0], [0, 1], [1, 1], [1, 0]], dtype=np.float32)
    engine = KindredEngine(rows, embeddings)
    result = engine.recommend([0, 1], "print", 10)
    assert result.tolist() == [2]
