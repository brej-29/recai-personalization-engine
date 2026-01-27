import hashlib
from typing import Any


def stable_hash(value: Any) -> str:
    """Return a deterministic hash for a value for use in cache keys or IDs."""
    data = repr(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()