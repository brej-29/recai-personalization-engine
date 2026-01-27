import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional

from fastapi import Request

from .config import get_settings
from .metrics import record_request
from .rate_limit import check_rate_limit

request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    return request_id_ctx_var.get()


def set_request_id(request_id: str) -> None:
    request_id_ctx_var.set(request_id)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_record: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }

        if hasattr(record, "request_id") and record.request_id:
            log_record["request_id"] = record.request_id

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    request_filter = RequestIdFilter()
    handler.addFilter(request_filter)

    root_logger.addHandler(handler)


async def logging_middleware(request: Request, call_next: Callable) -> Any:
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    set_request_id(request_id)

    # Optional per-IP rate limiting
    client_ip = request.client.host if request.client else None
    check_rate_limit(client_ip)

    logger = logging.getLogger("app.request")
    logger.info(
        json.dumps(
            {
                "event": "request_start",
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        )
    )

    response: Any = None
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception(
            json.dumps(
                {
                    "event": "request_exception",
                    "method": request.method,
                    "path": request.url.path,
                }
            )
        )
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        status_code = getattr(response, "status_code", 500) if response is not None else 500
        record_request(latency_ms=latency_ms, status_code=status_code)
        logger.info(
            json.dumps(
                {
                    "event": "request_end",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": round(latency_ms, 2),
                }
            )
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id