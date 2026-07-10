from __future__ import annotations

from typing import Any

from fastapi import status


class AppError(Exception):
    code = 40000
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    code = 40400
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    code = 40900
    status_code = status.HTTP_409_CONFLICT


class ValidationAppError(AppError):
    code = 40001
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class ExportError(AppError):
    code = 50020
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class ReviewExecutionError(AppError):
    code = 50030
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
