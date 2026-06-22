from __future__ import annotations

from typing import Any

from fastapi import Request


def request_id_from(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return str(request_id or "req_unknown")


def success(data: Any, request: Request, message: str = "success") -> dict[str, Any]:
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": request_id_from(request),
    }


def failure(
    code: int,
    message: str,
    request: Request,
    details: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "request_id": request_id_from(request),
    }
