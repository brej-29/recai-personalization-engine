import logging
from http import HTTPStatus
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .exceptions import AppError
from .logging import get_request_id

logger = logging.getLogger(__name__)


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": get_request_id(),
    }
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def init_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # type: ignore[override]
        logger.warning(
            "AppError: %s %s - %s",
            request.method,
            request.url.path,
            exc.message,
        )
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(  # type: ignore[override]
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "RequestValidationError: %s %s - %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return _error_response(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(  # type: ignore[override]
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.info(
            "PydanticValidationError: %s %s - %s",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return _error_response(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # type: ignore[override]
        logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
        return _error_response(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="Internal server error",
        )