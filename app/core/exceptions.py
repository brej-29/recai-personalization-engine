"""Custom application exceptions."""

from http import HTTPStatus
from typing import Any, Optional


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: Optional[Any] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(code="not_found", message=message, status_code=HTTPStatus.NOT_FOUND, details=details)


class ValidationAppError(AppError):
    def __init__(self, message: str = "Invalid request", details: Optional[Any] = None):
        super().__init__(
            code="validation_error",
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", details: Optional[Any] = None):
        super().__init__(
            code="conflict",
            message=message,
            status_code=HTTPStatus.CONFLICT,
            details=details,
        )