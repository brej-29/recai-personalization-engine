import numpy as np

from kindred.eval.run_ml import (
    crossover_k,
    imdb_catalog_id,
    item_knn_similarity,
    join_catalogue_movies,
    rank_item_knn,
    seed_holdout,
)


def test_imdb_id_join_uses_tt_and_zero_padding():
    assert imdb_catalog_id("114709") == "im:tt0114709"
    rows = [
        {"id": "im:tt0114709", "medium": "movie"},
        {"id": "al:1", "medium": "anime"},
    ]
    links = [{"movieId": "1", "imdbId": "114709"}, {"movieId": "2", "imdbId": "9999999"}]
    assert join_catalogue_movies(rows, links) == [(1, 0)]


def test_k_seed_split_is_deterministic_and_disjoint():
    left = seed_holdout(range(20), 5, np.random.default_rng(13))
    right = seed_holdout(range(20), 5, np.random.default_rng(13))
    assert np.array_equal(left[0], right[0])
    assert np.array_equal(left[1], right[1])
    assert set(left[0]).isdisjoint(left[1])
    assert len(left[0]) == 5
    assert len(left[1]) == 15


def test_item_knn_prefers_the_item_with_more_co_ratings():
    user_item = np.asarray([[1, 1, 0], [1, 1, 0], [1, 0, 1]], dtype=float)
    similarity = item_knn_similarity(user_item)
    ranking = rank_item_knn(similarity, [0], [1, 2])
    assert ranking.tolist() == [1, 2]


def test_crossover_requires_a_paired_ci_separated_gain():
    by_k = {
        1: (np.asarray([0.2, 0.2, 0.2]), np.asarray([0.3, 0.3, 0.3])),
        3: (np.asarray([0.8, 0.8, 0.8]), np.asarray([0.2, 0.2, 0.2])),
    }
    crossover, evidence = crossover_k(by_k, n_resamples=500, seed=13)
    assert crossover == 3
    assert evidence["3"]["ci_low"] > 0
