# Product

<!-- impeccable:product-schema 1 -->

> Inferred from the owner's brief (no interview round: the owner delegated all creative decisions and asked for autonomous work). Inferred facts are marked (assumed).

## Platform

web

## Stack

React + Vite + TypeScript, static site (GitHub Pages), all recommendation compute in the browser from precomputed artifacts. Chosen by the owner's delegation.

## Users

Fans who consume across media and are stuck in silos: someone who finished an anime and wants the manga or manhwa that scratches the same itch, a manhwa reader looking for a series or film with the same tone, a film fan curious about anime. Also (assumed) hiring managers and ML engineers reading the project as a case study, who need to see the measured evidence inside the product.

## Product Purpose

Kindred takes one or a few titles a person loved and returns kindred titles in every medium: anime, anime films, manga, manhwa, manhua, novels, movies, series, each browsable on its own. It exists because recommendation signals are siloed by medium. Success: a visitor names a title, sees credible cross-medium picks with reasons in seconds, and can verify how well the method works against a published benchmark.

## Positioning

Cross-media taste transfer, measured. Platforms recommend inside their own catalogue; Kindred recommends across catalogues using content representation plus a taste adapter learned from same-medium recommendation edges, and publishes the benchmark, baselines and failures.

## Operating Context

Runs entirely client-side from static files (no server, no cold start, no quota). Catalogue: 12.8k titles from AniList (anime, manga, manhwa, manhua, novels), IMDb non-commercial datasets and Wikipedia (movies, series). Evaluation artifacts live in `results/`.

## Capabilities and Constraints

- Search a title, pick up to five seeds, filter results by medium.
- Per-result explanation from shared genres/themes (no generated text).
- Map view of the catalogue by embedding projection.
- Evidence view built from `results/*.json`: benchmark, baselines, ablations, limits.
- No accounts, no tracking, no user data leaves the browser.
- Data attribution is mandatory: AniList (unofficial, non-commercial), Wikipedia (CC BY-SA), IMDb non-commercial dataset, MovieLens (GroupLens). Raw descriptions are not redistributed.
- Undecided: LLM-based reranking (needs a key and a server; offline experiment only).

## Brand Commitments

Name: Kindred. Repo name stays recai-personalization-engine. Never use "AniList" as the product name; always state the app is unofficial where it appears.

## Evidence on Hand

`docs/PREREGISTRATION.md` (hypotheses and thresholds written before scoring). Benchmark results will appear in `results/xm.json`; none are shown until they exist. No testimonials, user counts or performance claims beyond what `results/` contains.

## Product Principles

1. Show the work: every claim in the UI traces to a file in `results/`.
2. Cross-medium first: the thing no single-medium site can do is the thing the interface leads with.
3. Honest uncertainty: say where the method is weak (franchises, proxy labels, obscure titles).
4. Instant and offline-capable: no spinners where a dot product will do.
5. Each medium is its own shelf; blending is a choice, not a default.

## Accessibility & Inclusion

WCAG 2.2 AA contrast, full keyboard use, visible focus, reduced-motion respected, no colour-only encoding on the map or charts (medium is also encoded by shape/label). Cover images carry alt text; art is hotlinked and optional.
