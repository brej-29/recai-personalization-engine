# Kindred handoff

Everything a new session, a recruiter conversation or a LinkedIn draft needs, in one file. Every number below comes from a file in this repo (path given) or from a command you can rerun. Anything I could not verify is marked **(unverified)**.

## 1. One-minute summary

| | |
|---|---|
| Name | Kindred (repo: `brej-29/recai-personalization-engine`) |
| Pitch | Name one title you loved, get its kin across anime, manga, manhwa, manhua, novels, movies and series. |
| Live | https://brej-29.github.io/recai-personalization-engine/ |
| Repo | https://github.com/brej-29/recai-personalization-engine |
| Default branch | `main` (you call it master). Old version tagged `backup/pre-rebuild-2026-11-02` |
| Stack | Python (uv, numpy, scikit-learn, sentence-transformers, torch) for data and evaluation. React + Vite + TypeScript for the app. GitHub Actions and GitHub Pages. |
| Cost | 0. Static site, no keys, no server, no quota. |
| Status | Shipped and verified live. Five rebuild PRs merged (#4 to #8), CI green. |
| Tests | 18 Python tests, 8 web tests (one checks the browser engine against the Python reference on the shipped files). |

## 2. The problem

Recommenders learn from people who rated the same things. Nobody rates an anime and its manga in one system, so taste never crosses formats and no site can recommend across them.

Evidence (AniList sample of 5,900 popular non-adult titles, `results/silo.json`, rerun with `uv run python -m kindred.stats`):

| Fact | Value |
|---|---|
| User recommendation links inside one format | 49,441 |
| Links from an anime to a manga or novel, or back | **0** |
| Anime that name a manga or novel as their source | 1,184 |

The original project was a MovieLens API with Postgres, Redis and Docker, a generic hybrid recommender and no stated problem or evidence. I kept the core idea (a multi-domain personalisation engine) and found the sharper problem inside it.

## 3. What was built

### Method

1. Fetch a bounded, rate-limited sample from AniList, plus IMDb datasets, Wikidata and Wikipedia leads for movies and series, plus TVmaze for series posters.
2. Build a catalogue of 12,809 titles.
3. Encode title text (never the title itself) with gte-small.
4. Train a small linear taste adapter (384 to 256 d, contrastive loss) on same-medium recommendation edges only.
5. Score = 1.5 x embedding cosine + 0.5 x tag/genre TF-IDF cosine + 0.1 x popularity z-score.
6. Ship the vectors and ranking logic as static files; the browser ranks all 12,809 titles per query (about 3 ms measured on my laptop, **(unverified on other devices)**).

### Catalogue size (`data/catalog.jsonl`, rebuilt by `kindred.build_catalog`)

| Medium | Titles |
|---|---:|
| Anime (TV and web) | 1,600 |
| Anime films | 500 |
| Manga | 1,500 |
| Manhwa | 1,200 |
| Manhua | 600 |
| Novels | 500 |
| Movies | 5,400 |
| Series | 1,509 |
| **Total** | **12,809** |

### The benchmark (pre-registered in `docs/PREREGISTRATION.md`)

No human labels exist for anime to manga fit, so the benchmark walks the one bridge that does exist: fans of anime A also like anime B, and B was adapted from manga T. The model sees only the text of A and must rank T among about 3,800 print titles (and the reverse). Franchises are removed and split 60/10/30 train/validation/test. Metric NDCG@10 with paired bootstrap 95% CIs. Test split scored once; a rerun reproduces `results/xm.json` byte for byte.

### Results (test, 1,086 queries, 11,667 pairs, `results/xm.json`)

| System | NDCG@10 |
|---|---:|
| Random | 0.004 |
| Most popular | 0.029 |
| Tags and genres TF-IDF (best non-learned) | 0.142 [0.131, 0.154] |
| Sentence embedding as is | 0.121 |
| Embedding + taste adapter | 0.141 |
| Adapter + tags | 0.187 |
| **Kindred (adapter + tags + popularity)** | **0.217 [0.203, 0.231]** |

| Hypothesis | Verdict |
|---|---|
| H1 embeddings beat tag baselines | Not supported (0.121 vs 0.142) |
| H2 centring per medium helps | Not supported (diff -0.001) |
| H3 adapter helps cross-medium by 10%+ | Supported (+16% relative) |
| H4 Kindred beats best baseline by 25%+ | Supported (+53% relative) |
| H5 franchise leakage inflates scores 1.5x | Not supported (ratio 1.11) |
| H6 adapter helps movie cold start | Mixed (tiny gains for two encoders, losses for two) |

Other findings worth knowing:

* Popularity bias: 29% of Kindred's top ten come from the most popular decile of titles, against 12% in the labels. Without the popularity term the score is 0.187 with a 5% share.
* On 117 genuine manga, manhwa and manhua cross-format queries (direct user links) the full system scores 0.286 against 0.163 for tags alone. Small sample.
* MovieLens 25M (`results/ml.md`): popularity and item-kNN beat content scoring by 3 to 5x from the first seed. Where ratings exist, use ratings.
* Qwen3-Embedding-0.6B gets 0.230 on the full system on test (vs 0.217 for the shipped gte-small) but is 18x larger than a browser should download, and validation picked gte-small.

### The product

* A seven-segment instrument UI (LED dark skin, LCD light skin), a dot-matrix atlas of all titles, up to five seeds, one shelf per medium, same-franchise filter, live ranking time.
* The evidence is inside the page: silo ledger (49,441 vs 0), benchmark diagram, scoreboard with intervals, hypotheses, MovieLens check, limits, how it runs.
* Series posters from TVmaze (1,487 of 1,509 have one). Anime and manga covers from AniList. Movies show a typographic tile.
* Design system recorded in `DESIGN.md`; product record in `PRODUCT.md`.

## 4. Repo map

| Path | What |
|---|---|
| `README.md` | Case study with media (banner, GIFs, flowcharts) |
| `docs/PREREGISTRATION.md` | Hypotheses and thresholds, written before scoring |
| `docs/DATA.md` | Sources, terms checked, what ships |
| `docs/img/` | Banner SVG, demo and evidence GIFs, screenshots |
| `kindred/fetch_anilist.py`, `fetch_wiki.py`, `fetch_tvmaze.py` | Data collection (rate limited, resumable) |
| `kindred/build_catalog.py`, `embed.py`, `atlas.py` | Catalogue, encoders, map projection |
| `kindred/engine.py` | The benchmarked scoring (numpy only) |
| `kindred/eval/` | Pairs, baselines, metrics, adapter, `run_xm.py`, `run_ml.py` |
| `kindred/export_web.py`, `export_evidence.py` | Pack static files and the numbers the page shows |
| `results/` | `xm.json`, `xm_ablation.md`, `xm_errors.md`, `ml.json`, `ml.md`, `silo.json`, `adapter_gte-small.npz` |
| `web/` | React app. `src/engine.ts` ports the scoring, `src/engine.test.ts` checks parity with Python |
| `.github/workflows/` | `ci.yml` (Python), `web.yml` (web), `pages.yml` (deploy) |

Git-excluded and local only: `data/` (raw pulls, embeddings), `.impeccable/` (design review artifacts) and local tool settings. A fresh clone cannot rebuild data without the fetch step.

### Commands

```bash
uv sync --extra dev && uv run pytest && uv run ruff check .      # Python checks
cd web && npm ci && npm test && npm run dev                      # web
uv sync --extra pipeline --extra dev && make reproduce           # all numbers from raw pulls (about an hour)
uv run python -m kindred.export_web --keep-atlas                 # repack web data without redoing the map
uv run python -m kindred.export_evidence                         # refresh the numbers shown in the page
```

Deploy: merging to `main` runs `pages.yml`, which builds `web/` and publishes to GitHub Pages. Pages was enabled with `gh api -X POST repos/brej-29/recai-personalization-engine/pages -f build_type=workflow`.

## 5. Problems faced and how they were solved

| Problem | What happened | Fix |
|---|---|---|
| No problem in the old project | A generic MovieLens API | Reframed around cross-medium taste and measured that the signal does not exist |
| No cross-medium ground truth | 0 anime to manga recommendation edges | Adaptation-bridged proxy benchmark, stated as a limit everywhere |
| AniList fetch returned empty anime | A null `countryOfOrigin` variable filtered on null instead of being skipped | Omit the variable when unset |
| Wikidata fetch crashed mid-run | Transient DNS failure | Retry wrapper with backoff |
| TVmaze fetch stalled, then crawled | A timeout killed the job, then single-threaded lookups took hours | Resumable file, retry on errors, 8 workers paced under the 20 calls per 10 s limit (about 40 minutes) |
| Hypotheses failed | Raw embeddings lost to tags, centring did nothing, franchise leakage was small | Reported as results. They shaped the product: tags stayed in the formula |
| Harness change after seeing validation | Centring switch and ablation rows added | Test split untouched until the final run; amendment recorded in `results/xm.json` |
| Popularity inflated the score | The popularity term helped NDCG but pulled results to the head | Disclosed with numbers; ablation row without it |
| MovieLens contradicted the premise | Ratings beat content 3 to 5x | Stated as "wrong tool for movie to movie" in the product |
| Seven-segment legibility | Numerals carried ghost diagonals from the 14-segment mask | Plain 7-segment mask for digits, ghosts kept for letters only |
| Mobile page was 860 px wide | Grid track grew to the scroller's min-content | `minmax(0, 1fr)` and `min-width: 0` |
| Headline ledger showed 0 | State seeded before the data loaded | State holds only animation frames; default shows the real value |
| Contrast failures | Faint text under 4.5:1 | Raised in both skins |
| Image sources for movies | IMDb has no image API, Wikipedia posters are non-free | TVmaze for series; TMDB needs a free key from you |
| AniList terms | Prohibit "mass collection" | Bounded sample, no descriptions shipped, attribution, removal plan in `docs/DATA.md` |
| Old commits | 10 older commits carry a co-author trailer naming a third-party bot (Cosine) | Not rewritten (no history rewrites on `main`) |

## 6. Decisions you may be asked about

* **Why pre-register?** Recommender evaluations are easy to fool yourself with. Writing thresholds first made the failures (H1, H2, H5) credible instead of embarrassing.
* **Why a browser-only app?** Free tier running out is the failure mode of most portfolio demos. Static files cannot sleep and have no quota.
* **Why keep tags if embeddings are the "modern" part?** Because the measurement said so: tags 0.142 vs embeddings 0.121, and together 0.217.
* **Why not ship Qwen3-Embedding?** 0.6B parameters. It is 6% better on test but not browser-sized, and validation chose gte-small.
* **Why are movies weak?** The adapter learned from anime and manga edges, there is no cross-medium label for live action, and MovieLens shows content loses to ratings.
* **Why no LLM re-ranker?** It needs a hosted key and a server. Not tried; no claim made about it.

## 7. Outstanding work and ideas

| Item | Needs | Notes |
|---|---|---|
| Movie posters | A free TMDB account and API key from you (do not paste it in chat; set it as an environment variable) | Look up by IMDb id, add the required TMDB attribution notice |
| Confirm AniList comfort | Your call | Delete `web/public/data/` and redeploy if AniList objects |
| In-browser "vibe search" | Work | Embed a free-text query with the same encoder in the browser (transformers.js) and rank with the adapter; opt-in download, honest cold-start UX |
| Multi-seed benchmark | Work | The app averages up to five seeds, unbenchmarked |
| Small human evaluation | Volunteers | Would replace the proxy labels with judgments |
| LLM re-ranker experiment | A key or a local model | Offline experiment only; report even if it fails |
| End-to-end UI tests in CI | Work | Playwright against the built site |
| Actions Node 20 deprecation warnings | Bump action versions | Cosmetic for now |
| Rewrite the 10 Cosine trailers | Your approval | Needs a history rewrite on `main`, so I did not do it |

## 8. Portfolio and LinkedIn material

### Claims that are safe to make

* Built a cross-medium recommender and evaluated it on a pre-registered benchmark: 0.217 NDCG@10 against 0.142 for the best non-learned baseline, test split scored once, rerun reproduces byte for byte.
* Found that no user recommendation link goes from anime to manga in 49,441 links (AniList sample).
* Three of five pre-registered hypotheses failed, and the failures changed the design.
* The whole app runs in the browser from about 5 MB of static files on free hosting; the browser engine is tested against the Python reference.

### Claims to avoid

* Do not say it was validated by humans, or that anime to movie recommendations are validated.
* Do not say it beats production recommenders or give user numbers (there are none).
* Do not say "AI-powered" without saying what the model does (a small embedding model plus a learned linear adapter).
* Do not use "AniList" as the product name; the project is unofficial.

### 30-second pitch

"Recommenders can't suggest a manga to an anime fan because those audiences never share ratings. I measured it: 49,441 recommendation links on AniList, zero from anime to manga. So I built Kindred, which reads what titles are about and learns a small taste adapter from the links that do exist inside each medium. On a benchmark I pre-registered, it scores 0.217 against 0.142 for the best baseline. It also failed three of my five hypotheses, which is in the write-up, and it runs entirely in your browser."

### Resume bullets

* Built a cross-media recommendation engine (12.8k titles, 8 media) with a learned contrastive adapter over sentence embeddings, fused with tag TF-IDF; +53% NDCG@10 over the best non-learned baseline on a pre-registered benchmark (95% CI excludes zero).
* Designed the evaluation: adaptation-bridged proxy labels, franchise-level splits, paired bootstrap intervals, test split scored once, byte-identical reruns.
* Shipped a zero-cost static app (React, TypeScript, GitHub Pages) with the Python engine ported to the browser and parity-tested on the shipped files.
* Reported negative results: embeddings alone lost to curated tags, and on MovieLens collaborative filtering beat content scoring 3 to 5x.

### LinkedIn post 1: the launch

> Anime fans and manga readers are the same people, but no recommender knows it.
>
> Platforms learn from people who rated the same things. Almost nobody rates an anime and its manga in one place. I checked on AniList: 49,441 user recommendation links between titles of the same format, and zero from an anime to a manga.
>
> So I built Kindred. You name one title you loved and it finds its kin across anime, manga, manhwa, manhua, novels, movies and series. It reads what each title is about, and it learns a small taste adapter from the links that do exist inside each medium.
>
> I wrote the benchmark and the success thresholds down before scoring anything. On the test split it reaches 0.217 NDCG@10 against 0.142 for the best non-learned baseline.
>
> It runs entirely in your browser from about 5 MB of files. No server, no keys, nothing you type leaves the page.
>
> Try it: https://brej-29.github.io/recai-personalization-engine/
> Case study and code: https://github.com/brej-29/recai-personalization-engine

### LinkedIn post 2: the failures

> Three of my five pre-registered hypotheses failed. Here is what I kept.
>
> I was building a cross-medium recommender and wrote down what I expected before scoring.
>
> I expected sentence embeddings to beat plain tags. They did not: 0.121 against 0.142.
> I expected a fix for the "modality gap" between media to help. It did nothing measurable.
> I expected franchise leakage to matter (my threshold was a 1.5x inflation). It added about 11%.
>
> What did work: a small adapter trained on the recommendations that exist inside each medium, combined with the tags. Together they score 0.217, which is 53% better than the best baseline.
>
> Then I checked MovieLens, where real ratings exist. Popularity and item-kNN beat my content scoring by 3 to 5x. So the product says plainly that Kindred is for crossing media, not for movie to movie.
>
> Writing the thresholds first is what made the bad results easy to publish.
>
> https://github.com/brej-29/recai-personalization-engine

### LinkedIn post 3: the interface and engineering

> I built the UI for my recommender as a seven-segment display.
>
> Numbers are drawn from one eight-segment mask, unlit segments are drawn too, and results stay in place while the segments change. There is an LED skin for dark and an LCD calculator skin for light.
>
> The less visible part: the scoring runs in the browser, ported from the Python engine I benchmarked. A test loads the shipped files and checks that both give the same top results, so the numbers on the page describe what actually runs.
>
> Static files on GitHub Pages, so it cannot go to sleep and has no quota.
>
> Live: https://brej-29.github.io/recai-personalization-engine/

### Carousel outline (8 slides)

1. 49,441 vs 0 (the silo, screenshot `docs/img/silo.png`)
2. How the benchmark walks anime A to B to manga T (flowchart from the README)
3. What I wrote down before scoring (hypotheses table)
4. Scoreboard (`docs/img/scoreboard.png`)
5. What failed (H1, H2, H5)
6. Where it is the wrong tool (`docs/img/movies.png`)
7. The interface (`docs/img/hero-led.png`, `docs/img/hero-lcd.png`)
8. Link and what I would do next

### Interview questions you can expect

| Question | Short answer |
|---|---|
| How do you evaluate without labels? | Proxy labels from adaptation links, franchise-level splits so siblings cannot leak, paired bootstrap CIs, thresholds fixed in advance, test scored once. |
| Why did tags beat embeddings? | Curated tags encode exactly what fans recommend on (themes), plot text carries plot detail. The adapter reshapes embeddings toward recommendation similarity, and the two are complementary. |
| What is the adapter? | A linear map 384 to 256 trained with an in-batch contrastive loss on same-medium recommendation pairs, with val/test franchises removed from training. |
| What would you do with more time? | Human judgments, multi-seed evaluation, an offline LLM re-ranker experiment, TMDB posters, in-browser free-text search. |
| What is the biggest weakness? | Proxy labels, and live action is not validated across media. Both are in the app. |
| How do you know the browser matches Python? | A test loads the shipped arrays and compares top-12 lists against `reference_recommend`. |

### Visual assets (all in `docs/img/`)

| File | Use |
|---|---|
| `banner.svg` | Animated segment-display banner (README header, works as a LinkedIn banner when exported) |
| `demo.gif` | Search, shelves, second seed, LCD skin (about 3 MB) |
| `evidence.gif` | Scroll through the evidence (about 3 MB) |
| `hero-led.png`, `hero-lcd.png`, `mobile-led.png` | First-viewport screenshots |
| `silo.png`, `test.png`, `scoreboard.png`, `movies.png` | Section screenshots for posts and slides |

Hashtag ideas: #recommendersystems #machinelearning #datascience #buildinpublic #opensource

## 9. People, accounts and terms

* GitHub: `brej-29`. Pages enabled from the Actions workflow.
* Data terms are in `docs/DATA.md`: AniList (non-commercial, no mass collection, unofficial), IMDb non-commercial datasets, Wikipedia (CC BY-SA), TVmaze (CC BY-SA, hot-linking allowed), MovieLens (research use, no redistribution).
* The app is non-commercial, ad-free and tracks nothing.
