# Pre-registration: does taste transfer across media?

Written 2026-11-02, before any model was scored. Only catalogue counts had been inspected (to
check the benchmark is feasible), listed under "What I had seen".

## Problem

Recommendation signals are siloed by medium. A fan of one anime gets "more anime"; the manga,
manhwa or novel they would love is invisible, because almost nobody has rated both in the same
system, so collaborative filtering has nothing to join on.

## What I had seen before writing this

| Fact (AniList sample, 5,900 titles, fetched 2026-11-02) | Value |
|---|---|
| Directed user-recommendation edges, rating >= 2, same family | 49,441 |
| Same, across families (all of them inside AniList's MANGA type: manga / manhwa / manhua) | 578 |
| Anime to manga/novel recommendation edges | 0 |
| Anime titles with a manga/novel source in the sample | 1,185 |

Direct cross-type ground truth does not exist, so the benchmark below uses a labelled proxy.

## Benchmark XM (cross-media, adaptation-bridged)

* **Catalogue.** Top titles by AniList popularity, non-adult: 1,600 TV/ONA anime, 500 anime
  films, 1,500 manga, 1,200 manhwa, 600 manhua, 500 novels. Two types: ANIME and PRINT
  (manga, manhwa, manhua, novel).
* **Query / relevant pair.** Query `A` of one type. Relevant target `T` of the other type if
  some `B` of `A`'s type has a user-recommendation edge with `A` (either direction, net rating
  >= 2) and `T` is `B`'s adaptation (relation ADAPTATION/SOURCE). In words: "people who liked
  A also liked B, and B comes from T".
* **Leakage filter.** Drop pairs where `T` is in the same relation-graph component
  (any relation type) as `A`.
* **Input.** The model sees only text built from description, genres and tags. Titles are
  never embedded.
* **Candidates.** All catalogue items of the other type except those in `A`'s component.
* **Split.** Relation-graph components are assigned to train 60% / val 10% / test 30% with seed
  13. Queries are drawn from val and test components. All training edges incident to any
  val/test-component item are removed, so no trained method has seen a test query's neighbours.
* **Metrics.** NDCG@10 (primary), Recall@10, MRR, hit-rate@10, plus catalogue coverage and
  mean popularity-rank of the top 10. Uncertainty: paired bootstrap over queries, 10,000
  resamples, 95% CI.
* **Known weakness.** Labels are a proxy built from adaptation links, so they reward
  recommending titles that have an anime or print counterpart. Reported as a limit, and a
  secondary check uses the 335 genuine manga/manhwa/manhua cross-format pairs.

## Systems

Baselines: random; popularity; genre Jaccard; tag-TF-IDF cosine; description-TF-IDF cosine;
zero-shot dense encoders (all-MiniLM-L6-v2, bge-small-en-v1.5, gte-small, browser-deployable;
Qwen3-Embedding-0.6B as an offline ceiling).

Proposed (Kindred): best browser-deployable encoder, plus (a) per-type mean-centering of
embeddings, (b) a linear adapter trained with InfoNCE on same-type recommendation edges only,
(c) late fusion with the tag channel and a popularity prior. Hyperparameters are chosen on
val only; the test set is scored once per final configuration.

## Hypotheses and thresholds

| ID | Hypothesis | Counts as supported if |
|---|---|---|
| H1 | Dense text encoders beat tag, genre and popularity baselines on XM | NDCG@10 of best zero-shot encoder > best non-dense baseline, CI of paired diff excludes 0 |
| H2 | Type-centering helps (embedding "modality gap", Liang et al. 2022) | relative NDCG@10 gain >= 5%, CI excludes 0 |
| H3 | A same-type-trained adapter transfers to cross-type | relative NDCG@10 gain >= 10% over best zero-shot, CI excludes 0 |
| H4 | Kindred (full) beats the best non-learned baseline | relative NDCG@10 gain >= 25%, CI excludes 0 |
| H5 | Franchise leakage inflates scores | NDCG@10 without the component filter >= 1.5x the filtered score |
| H6 | Adapter trained on anime/manga also helps movie to movie cold start (MovieLens) | Recall@10 gain over zero-shot, CI excludes 0 |

If H3 or H4 fail, that is reported as the headline, not hidden.

## Benchmark ML (live-action sanity check)

MovieLens 25M, users with >= 20 ratings of >= 4 stars on catalogue movies; seed = k liked
movies (k in 1, 3, 5, 10), hold out the rest, metrics as above. Baselines: popularity, item-kNN
on co-ratings, dense text, Kindred. Purpose: check the engine is sane on a domain where
ordinary collaborative filtering works, and find the k where CF overtakes content.

## Reproducibility

`make reproduce` rebuilds every number from raw API pulls (dates and sample sizes above). Seeds
fixed. Raw data is not redistributed; fetch scripts are.
