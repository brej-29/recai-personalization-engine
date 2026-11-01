"""Encode catalogue text with sentence-transformers; writes data/emb/<name>.npy (L2-normalised)."""
import json
import sys
from pathlib import Path

import numpy as np

MODELS = {
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "bge-small": "BAAI/bge-small-en-v1.5",
    "gte-small": "thenlper/gte-small",
    "qwen3-0.6b": "Qwen/Qwen3-Embedding-0.6B",
}


def load_texts(path: str = "data/catalog.jsonl") -> list[str]:
    return [json.loads(line)["text"] for line in open(path, encoding="utf-8")]


def encode(name: str, texts: list[str], batch: int = 64) -> np.ndarray:
    import torch
    from sentence_transformers import SentenceTransformer

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    kw = {"model_kwargs": {"torch_dtype": torch.float16}} if dev == "cuda" else {}
    model = SentenceTransformer(MODELS[name], device=dev, **kw)
    model.max_seq_length = 384
    vecs = model.encode(texts, batch_size=batch, normalize_embeddings=True, show_progress_bar=True)
    return vecs.astype(np.float32)


if __name__ == "__main__":
    out = Path("data/emb")
    out.mkdir(parents=True, exist_ok=True)
    texts = load_texts()
    for name in sys.argv[1:] or ["minilm", "bge-small", "gte-small"]:
        np.save(out / f"{name}.npy", encode(name, texts))
        print(name, "done")
