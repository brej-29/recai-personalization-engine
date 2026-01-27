from __future__ import annotations

import argparse
import logging
import pickle

import numpy as np
from implicit.als import AlternatingLeastSquares
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.model_registry import TrainingResult, register_model_version
from app.training.data_prep import build_implicit_matrix, load_interactions, load_items
from app.training.eval import evaluate_recommender

logger = logging.getLogger(__name__)
settings = get_settings()


def train_content_model(db: Session) -> TrainingResult:
    """Train TF-IDF content-based model from items table."""
    items_df = load_items(db)
    if items_df.empty:
        return TrainingResult(success=False, message="No items available for content model.")

    items_df["text_blob"] = (
        items_df["title"].fillna("")
        + " "
        + items_df["genres"].fillna("")
        + " "
        + items_df["text"].fillna("")
    )

    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    matrix = vectorizer.fit_transform(items_df["text_blob"].tolist())

    artifact_dir = settings.artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "content_tfidf.pkl"

    data = {
        "vectorizer": vectorizer,
        "item_ids": items_df["id"].to_numpy(dtype=np.int64),
        "item_titles": items_df["title"].tolist(),
        "item_matrix": matrix.toarray().astype(np.float32),
    }
    with artifact_path.open("wb") as f:
        pickle.dump(data, f)

    # Very simple evaluation: treat last interaction of each user as relevant and
    # compute metrics on a hold-out set.
    interactions_df = load_interactions(db)
    if interactions_df.empty:
        metrics = {"recall_at_k": 0.0, "ndcg_at_k": 0.0}
    else:
        interactions_df = interactions_df.sort_values("ts")
        last = interactions_df.groupby("user_id").tail(1)

        # Build a simple recommender usage on the training interactions:
        from app.recommenders.content_tfidf import ContentModelArtifact, ContentRecommender

        artifact = ContentModelArtifact(
            vectorizer=vectorizer,
            item_ids=data["item_ids"],
            item_titles=data["item_titles"],
            item_matrix=data["item_matrix"],
        )
        rec_engine = ContentRecommender(db=db, artifact=artifact)

        user_recs = {}
        user_relevant = {}
        for user_id, group in last.groupby("user_id"):
            user_relevant[user_id] = group["item_id"].tolist()
            user_recs[user_id] = [r.item_id for r in rec_engine.recommend(user_id=int(user_id), limit=20)]

        metrics = evaluate_recommender(user_recs, user_relevant, k=10)

    mv, version = register_model_version(
        db,
        name="content_tfidf",
        metrics=metrics,
        artifact_path=artifact_path,
    )
    logger.info("Trained content TF-IDF model version %s at %s", version, artifact_path)
    return TrainingResult(
        success=True,
        message="Content model trained",
        version=version,
        metrics=metrics,
        path=str(mv.path),
    )


def train_mf_model(db: Session) -> TrainingResult:
    """Train implicit ALS matrix factorization model."""
    interactions_df = load_interactions(db)
    if interactions_df.empty:
        return TrainingResult(success=False, message="No interactions available for MF model.")

    user_ids, item_ids, data = build_implicit_matrix(interactions_df)

    unique_user_ids = np.unique(user_ids)
    unique_item_ids = np.unique(item_ids)

    user_id_to_index = {int(uid): idx for idx, uid in enumerate(unique_user_ids)}
    item_id_to_index = {int(iid): idx for idx, iid in enumerate(unique_item_ids)}

    user_indices = np.array([user_id_to_index[int(u)] for u in user_ids], dtype=np.int64)
    item_indices = np.array([item_id_to_index[int(i)] for i in item_ids], dtype=np.int64)

    n_users = len(unique_user_ids)
    n_items = len(unique_item_ids)
    matrix = sparse.coo_matrix((data, (user_indices, item_indices)), shape=(n_users, n_items))

    model = AlternatingLeastSquares(
        factors=64,
        regularization=0.01,
        iterations=15,
        random_state=42,
    )
    # implicit expects item-user matrix
    model.fit(matrix.T.tocsr())

    user_factors = model.user_factors.astype(np.float32)
    item_factors = model.item_factors.astype(np.float32)

    artifact_dir = settings.artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "mf_als.pkl"

    data_dict = {
        "user_factors": user_factors,
        "item_factors": item_factors,
        "user_id_mapping": user_id_to_index,
        "item_id_mapping": item_id_to_index,
    }
    with artifact_path.open("wb") as f:
        pickle.dump(data_dict, f)

    # Simple evaluation: for each user, use MF scores to recommend and compare to last item
    interactions_df = interactions_df.sort_values("ts")
    last = interactions_df.groupby("user_id").tail(1)

    user_recs = {}
    user_relevant = {}
    for user_id, group in last.groupby("user_id"):
        uid = int(user_id)
        if uid not in user_id_to_index:
            continue
        uidx = user_id_to_index[uid]
        scores = user_factors[uidx] @ item_factors.T
        ranked_item_indices = np.argsort(-scores)
        inv_item_index = {idx: iid for iid, idx in item_id_to_index.items()}
        ranked_item_ids = [int(inv_item_index[i]) for i in ranked_item_indices]
        user_recs[uid] = ranked_item_ids
        user_relevant[uid] = group["item_id"].tolist()

    metrics = evaluate_recommender(user_recs, user_relevant, k=10)

    mv, version = register_model_version(
        db,
        name="mf_als",
        metrics=metrics,
        artifact_path=artifact_path,
    )
    logger.info("Trained MF ALS model version %s at %s", version, artifact_path)
    return TrainingResult(
        success=True,
        message="MF model trained",
        version=version,
        metrics=metrics,
        path=str(mv.path),
    )


if __name__ == "__main__":
    # Simple CLI entry point for manual training when running `python -m app.training.train`
    parser = argparse.ArgumentParser(description="Train RecAI models")
    parser.add_argument("--model", choices=["content", "mf"], required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.model == "content":
            res = train_content_model(db)
        else:
            res = train_mf_model(db)
        if res.success:
            print(f"Training successful: {res}")
        else:
            print(f"Training failed: {res.message}")
    finally:
        db.close()