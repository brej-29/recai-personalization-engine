# Data sources, terms and what ships

Raw pulls are gitignored under `data/raw/` and never redistributed. The repo ships fetch scripts and a compact derived artifact for the live app.

| Source | What is used | Terms checked | What ships in the repo |
|---|---|---|---|
| [AniList GraphQL API](https://docs.anilist.co) | Popularity-ranked sample of 5,900 non-adult titles: metadata, tags, relations, user recommendations | Free for non-commercial use; "hoarding or mass collection" and use as a backup/storage service are prohibited ([terms](https://github.com/AniList/ApiV2-GraphQL-Docs/blob/master/docs/guide/terms-of-use.md)). Fetcher is limited to 25 requests/minute, honours `Retry-After`, and takes a bounded sample, not the catalogue | Titles, year, genres, up to 6 theme names, score, popularity, cover path and AniList id per title, plus embeddings. No descriptions. Each result links back to AniList. This project is unofficial and not affiliated with AniList |
| [IMDb non-commercial datasets](https://developer.imdb.com/non-commercial-datasets/) | `title.basics` and `title.ratings` to choose movies and series with enough votes | Personal and non-commercial use | Title, year, genres, rating, vote count, IMDb id and link. No images |
| [Wikidata](https://www.wikidata.org) and [Wikipedia](https://en.wikipedia.org) | Genre, country of origin, English article title, lead paragraph | CC0 (Wikidata), CC BY-SA 4.0 (Wikipedia text) | Embeddings of the lead text only. The text itself is not shipped |
| [TVmaze API](https://www.tvmaze.com/api) | Series poster paths, looked up by IMDb id | CC BY-SA, free for any purpose with a link back, hot-linking the image CDN is allowed, 20 calls per 10 s ([terms](https://www.tvmaze.com/api)) | Poster path per series; images hot-linked at display time, attribution in the app footer |
| [MovieLens 25M](https://grouplens.org/datasets/movielens/25m/) | Ratings for the live-action sanity benchmark | Research use, no redistribution | Aggregate results only |

## Decisions that follow from the terms

* The app is non-commercial, ad-free and tracks nothing.
* Descriptions and Wikipedia text are used offline to compute embeddings and are not served.
* Cover art is hot-linked from AniList's CDN at display time, not copied. Series posters come from TVmaze. Movies have no poster source that is both free and clear to use without an account (IMDb has no image API and Wikipedia posters are non-free), so they get a typographic tile.
* If AniList asks for the derived catalogue to be removed, delete `web/public/data/` and redeploy; the benchmark numbers remain reproducible by anyone who re-runs the fetch.

## Known data limits

* The AniList sample is the most popular titles, so obscure works are absent and popularity bias is baked into the catalogue.
* Movies and series are chosen by IMDb vote count (at least 40,000 for movies, 20,000 for series), which skews toward English-language and recent titles.
* Japanese animation that IMDb also lists is removed from the live-action side by Wikidata genre and origin, so it appears once, as anime.
* `docs/PREREGISTRATION.md` lists 1,185 anime with a manga or novel source, from an exploratory count made before the benchmark was written. The reproducible definition in `kindred/stats.py` gives 1,184 and is the number used everywhere else.
