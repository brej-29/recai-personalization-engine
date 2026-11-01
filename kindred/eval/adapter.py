"""Leakage-safe linear adapter training with an in-batch contrastive loss."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class AdapterResult:
    matrix: np.ndarray
    history: list[dict[str, float]]
    temperature: float
    epochs: int
    output_dim: int


def train_adapter(
    embeddings: np.ndarray,
    rows: list[dict],
    train_edges: list[tuple[int, int]],
    val_score: Callable[[np.ndarray], float] | None = None,
    output_dim: int | None = None,
    seed: int = 13,
    epochs: int = 8,
    batch_size: int = 512,
    temperatures: tuple[float, ...] = (0.05, 0.07, 0.1),
    patience: int = 2,
    output_dims: tuple[int, ...] | None = None,
) -> AdapterResult:
    """Train on same-family edges; validation is supplied by the caller."""
    del rows
    try:
        import torch
    except ImportError:
        identity = np.eye(embeddings.shape[1], dtype=np.float32)
        return AdapterResult(identity, [], temperatures[0], 0, embeddings.shape[1])

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    source = np.asarray(embeddings, dtype=np.float32)
    dimension = source.shape[1]
    if output_dims is None:
        output_dims = (output_dim,) if output_dim is not None else (
            (128, 256) if dimension >= 256 else (min(128, dimension),)
        )
    if not train_edges:
        return AdapterResult(np.eye(dimension, dtype=np.float32), [], temperatures[0], 0, dimension)

    edge_array = np.asarray(train_edges, dtype=np.int64)
    rng = np.random.default_rng(seed)
    best_global: tuple[float, np.ndarray, float, int, int] | None = None
    all_history: list[dict[str, float]] = []

    for requested_dim in output_dims:
        for temperature in temperatures:
            layer = torch.nn.Linear(dimension, requested_dim, bias=False, device=device)
            torch.nn.init.orthogonal_(layer.weight)
            optimizer = torch.optim.AdamW(layer.parameters(), lr=2e-3, weight_decay=1e-4)
            best_score = -np.inf
            best_state = layer.weight.detach().cpu().numpy().copy()
            stale = 0
            for epoch in range(epochs):
                order = rng.permutation(len(edge_array))
                losses = []
                layer.train()
                for start in range(0, len(order), batch_size):
                    batch = edge_array[order[start:start + batch_size]]
                    left = torch.as_tensor(source[batch[:, 0]], device=device)
                    right = torch.as_tensor(source[batch[:, 1]], device=device)
                    left_z = torch.nn.functional.normalize(layer(left), dim=1)
                    right_z = torch.nn.functional.normalize(layer(right), dim=1)
                    logits = left_z @ right_z.T / temperature
                    labels = torch.arange(logits.shape[0], device=device)
                    loss = (torch.nn.functional.cross_entropy(logits, labels)
                            + torch.nn.functional.cross_entropy(logits.T, labels)) / 2
                    optimizer.zero_grad(set_to_none=True)
                    loss.backward()
                    optimizer.step()
                    losses.append(float(loss.detach().cpu()))
                matrix = layer.weight.detach().cpu().numpy().T.astype(np.float32)
                score = float(val_score(matrix)) if val_score is not None else -float(np.mean(losses))
                all_history.append({"output_dim": requested_dim, "temperature": temperature,
                                    "epoch": epoch + 1, "loss": float(np.mean(losses)),
                                    "val_ndcg@10": score})
                if score > best_score + 1e-12:
                    best_score = score
                    best_state = layer.weight.detach().cpu().numpy().copy()
                    stale = 0
                else:
                    stale += 1
                if stale >= patience:
                    break
            if best_global is None or best_score > best_global[0]:
                best_global = (best_score, best_state, temperature, len(all_history), requested_dim)

    assert best_global is not None
    return AdapterResult(
        matrix=best_global[1].T.astype(np.float32),
        history=all_history,
        temperature=float(best_global[2]),
        epochs=int(best_global[3]),
        output_dim=int(best_global[4]),
    )


def save_adapter(result: AdapterResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, W=result.matrix, temperature=result.temperature)
