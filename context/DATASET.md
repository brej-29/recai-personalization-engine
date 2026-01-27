# Dataset – MovieLens 1M

RecAI’s MVP uses the **MovieLens 1M** dataset as its reference dataset.

---

## Source

- GroupLens project: https://grouplens.org/datasets/movielens/1m/
- License: Provided by GroupLens for research and non-commercial use (see their terms).

We do **not** redistribute the raw data in this repository.  
Instead, `scripts/download_movielens_1m.py` downloads it into the local `data/` directory.

---

## Files

After download and extraction, MovieLens 1M exposes these key files:

- `users.dat`
- `movies.dat`
- `ratings.dat`

They are pipe-separated (`::`) files with specific schemas.

---

## Schemas

### users.dat

```text
UserID::Gender::Age::Occupation::Zip-code
```

- `UserID` – integer key (1..6040)
- `Gender` – `M` or `F`
- `Age` – coded age group (e.g. 18, 25, 35, 45, 50, 56)
- `Occupation` – integer occupation code
- `Zip-code` – string

In Postgres, this maps to:

- `users.id` – `UserID`
- `users.attributes` – JSON containing gender, age, occupation, zip.

### movies.dat

```text
MovieID::Title::Genres
```

- `MovieID` – integer key
- `Title` – movie title (with year)
- `Genres` – pipe-separated list, e.g. `Action|Sci-Fi`

In Postgres, this maps to:

- `items.id` – `MovieID`
- `items.title` – `Title`
- `items.genres` – `Genres` as a single pipe-separated string
- `items.text` – derived text blob: `title + " " + genres`
- `items.metadata` – optional JSON for extra attributes (currently minimal).

### ratings.dat

```text
UserID::MovieID::Rating::Timestamp
```

- `Rating` – explicit rating from 1 to 5.
- `Timestamp` – UNIX timestamp (seconds).

In Postgres, this maps to:

- `interactions.user_id` – `UserID`
- `interactions.item_id` – `MovieID`
- `interactions.rating` – `Rating`
- `interactions.event_type` – `"rate"` by default for these rows.
- `interactions.ts` – converted to `TIMESTAMP WITH TIME ZONE`.

---

## Derived Fields

For content-based recommendations we derive:

- `items.text`:
  - `title + " " + genres`
  - This is the text field used to build TF‑IDF vectors.

For implicit feedback we derive:

- `event_type`:
  - Ratings are treated as an implicit signal with type `"rate"`.
  - Later we can include other event types (views, clicks) from real logs.

---

## Assumptions & Simplifications

- We treat MovieLens as **single-domain (movies)** but the schema is generic:
  - Other domains (products, articles) should also map to `items` and `interactions`.
- We do not currently use demographic fields directly in the models:
  - They are stored in `users.attributes` for potential future use.
- We only support English text for TF‑IDF in the MVP.

---

## Local Data Layout

By default, data is expected under:

```text
data/
  raw/
    ml-1m/
      users.dat
      movies.dat
      ratings.dat
```

You can override the base data directory using `DATA_DIR` in the environment.

Scripts:

- `scripts/download_movielens_1m.py` – creates `data/raw/ml-1m/` and downloads the zip.
- `scripts/seed_db.py` – reads `*.dat` files and populates Postgres tables.