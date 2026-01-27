from __future__ import annotations

import time
from typing import Dict, Tuple

from app.core.config import get_settings
from app.core.exceptions import AppError


# Simple per-IP, per-minute rate limiter for optional production hardening.
_state: Dict[str, Tuple[int, float]] = {}


def check_rate_limit(client_ip: str | None) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled or not client_ip:
        return

    max_requests = settings.rate_limit_requests_per_min
    now = time.time()
    window_seconds = 60.0

    count, window_start = _state.get(client_ip, (0, now))
    if now - window_start >= window_seconds:
        # New window
        count = 0
        window_start = now

    count += 1
    _state[client_ip] = (count, window_start)

    if count > max_requests:
        raise AppError(
            status_code=429,
            code="rate_limited",
            message="Too many requests, please slow down.",
        )