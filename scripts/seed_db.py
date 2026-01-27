import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Interaction, Item, User
from app.utils.timing import timed


def parse_users(path: Path) -> Dict[int, dict]:
    users: Dict[int, dict] = {}
    with path.open("r", encoding="latin-1") as f:
        for line in f:
            user_id_str, gender, age, occupation, zip_code = line.strip().split("::")
            user_id = int(user_id_str)
            users[user_id] = {
                "gender": gender,
                "age": int(age),
                "occupation": int(occupation),
                "zip": zip_code,
            }
    return users


def parse_movies(path: Path) -> Dict[int, dict]:
    movies: Dict[int, dict] = {}
    with path.open("r", encoding="latin-1") as f:
        for line in f:
            movie_id_str, title, genres = line.strip().split("::")
            movie_id = int(movie_id_str)
            movies[movie_id] = {
                "title": title,
                "genres": genres,
                "text": f"{title} {genres}",
            }
    return movies


def seed(database_url: str, data_dir: Path) -> None:
    raw_dir = data_dir / "raw" / "ml-1m"
    users_path = raw_dir / "users.dat"
    movies_path = raw_dir / "movies.dat"
    ratings_path = raw_dir / "ratings.dat"

    if not users_path.exists() or not movies_path.exists() or not ratings_path.exists():
        raise SystemExit(
            f"MovieLens 1M files not found under {raw_dir}. "
            "Run scripts/download_movielens_1m.py first."
        )

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)

    users_map = parse_users(users_path)
    movies_map = parse_movies(movies_path)

    with Session(engine) as session:
        with timed("Seeding users"):
            for uid, attrs in users_map.items():
                session.add(
                    User(
                        id=uid,
                        attributes=attrs,
                        created_at=datetime.now(timezone.utc),
                    )
                )
            session.commit()

        with timed("Seeding items"):
            for mid, attrs in movies_map.items():
                session.add(
                    Item(
                        id=mid,
                        title=attrs["title"],
                        genres=attrs["genres"],
                        text=attrs["text"],
                    )
                )
            session.commit()

        with timed("Seeding interactions (ratings)"):
            batch_size = 10_000
            batch: list[Interaction] = []
            with ratings_path.open("r", encoding="latin-1") as f:
                for _idx, line in enumerate(f, start=1):
                    user_id_str, movie_id_str, rating_str, ts_str = line.strip().split("::")
                    ts = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                    batch.append(
                        Interaction(
                            user_id=int(user_id_str),
                            item_id=int(movie_id_str),
                            event_type="rate",
                            rating=float(rating_str),
                            ts=ts,
                        )
                    )
                    if len(batch) >= batch_size:
                        session.bulk_save_objects(batch)
                        session.commit()
                        batch.clear()
                if batch:
                    session.bulk_save_objects(batch)
                    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Postgres DB from MovieLens 1M dataset")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/recai"),
        help="SQLAlchemy database URL",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.getenv("DATA_DIR", "data")),
        help="Base data directory",
    )
    args = parser.parse_args()

    print(f"[INFO] Seeding DB at {args.database_url}")
    print(f"[INFO] Using data directory {args.data_dir}")
    seed(args.database_url, args.data_dir)
    print("[OK] Seeding complete.")


if __name__ == "__main__":
    main()