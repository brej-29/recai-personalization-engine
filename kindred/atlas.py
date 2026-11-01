"""2-D projection of the catalogue for the map view (UMAP on the shipped embedding)."""
import sys

import numpy as np


def project(vecs: np.ndarray, seed: int = 13) -> np.ndarray:
    import umap

    xy = umap.UMAP(n_neighbors=25, min_dist=0.12, metric="cosine", random_state=seed).fit_transform(vecs)
    xy -= xy.min(0)
    return (xy / xy.max(0)).astype(np.float32)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/emb/minilm.npy"
    np.save("data/atlas.npy", project(np.load(src)))
    print("atlas saved")
