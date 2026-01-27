from __future__ import annotations

from typing import Dict


# Simple in-memory metrics for MVP. This is process-local and not persisted.
_request_count: int = 0
_error_count: int = 0
_cache_hit_count: int = 0
_cache_miss_count: int = 0

_latency_buckets: Dict[str, int] = {
    "50": 0,    # <= 50ms
    "100": 0,   # <= 100ms
    "250": 0,   # <= 250ms
    "500": 0,   # <= 500ms
    "inf": 0,   # > 500ms
}
_latency_sum: float = 0.0
_latency_count: int = 0


def record_request(latency_ms: float, status_code: int) -> None:
    global _request_count, _latency_sum, _latency_count

    _request_count += 1
    _latency_sum += latency_ms
    _latency_count += 1

    bucket: str
    if latency_ms <= 50:
        bucket = "50"
    elif latency_ms <= 100:
        bucket = "100"
    elif latency_ms <= 250:
        bucket = "250"
    elif latency_ms <= 500:
        bucket = "500"
    else:
        bucket = "inf"
    _latency_buckets[bucket] += 1


def increment_error() -> None:
    global _error_count
    _error_count += 1


def increment_cache_hit() -> None:
    global _cache_hit_count
    _cache_hit_count += 1


def increment_cache_miss() -> None:
    global _cache_miss_count
    _cache_miss_count += 1


def export_metrics_text() -> str:
    """Return a Prometheus-style plain text metrics snapshot."""
    lines = [
        "# HELP recai_request_count Total HTTP requests",
        "# TYPE recai_request_count counter",
        f"recai_request_count {_request_count}",
        "# HELP recai_error_count Total error responses",
        "# TYPE recai_error_count counter",
        f"recai_error_count {_error_count}",
        "# HELP recai_cache_hit_count Cache hits for recommendation lookups",
        "# TYPE recai_cache_hit_count counter",
        f"recai_cache_hit_count {_cache_hit_count}",
        "# HELP recai_cache_miss_count Cache misses for recommendation lookups",
        "# TYPE recai_cache_miss_count counter",
        f"recai_cache_miss_count {_cache_miss_count}",
        "# HELP recai_latency_ms Request latency in milliseconds",
        "# TYPE recai_latency_ms histogram",
    ]

    # Histogram buckets
    cumulative = 0
    for le in ["50", "100", "250", "500", "inf"]:
        count = _latency_buckets[le]
        cumulative += count
        lines.append(f'recai_latency_ms_bucket{{le="{le}"}} {cumulative}')
    lines.append(f"recai_latency_ms_count {_latency_count}")
    lines.append(f"recai_latency_ms_sum {_latency_sum:.3f}")

    avg_latency = (_latency_sum / _latency_count) if _latency_count > 0 else 0.0
    lines.extend(
        [
            "# HELP recai_latency_ms_avg Average request latency in milliseconds",
            "# TYPE recai_latency_ms_avg gauge",
            f"recai_latency_ms_avg {avg_latency:.3f}",
        ]
    )

    return "\n".join(lines) + "\n"