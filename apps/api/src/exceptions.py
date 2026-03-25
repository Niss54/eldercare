from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorField(BaseModel):
    loc: list[str]
    msg: str
    type: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[ErrorField] | None = None


def _problem(
    request: Request,
    title: str,
    status_code: int,
    error: ErrorDetail,
    error_type: str = "about:blank",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "type": error_type,
            "title": title,
            "status": status_code,
            "detail": error.message,
            "error": error.model_dump(),
            "instance": str(request.url.path),
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _problem(
        request=request,
        title="HTTP Error",
        status_code=exc.status_code,
        error=ErrorDetail(code=f"http_{exc.status_code}", message=detail),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: list[ErrorField] = []
    for item in exc.errors():
        loc = [str(piece) for piece in item.get("loc", [])]
        fields.append(
            ErrorField(
                loc=loc,
                msg=str(item.get("msg", "invalid value")),
                type=str(item.get("type", "validation_error")),
            )
        )
    return _problem(
        request=request,
        title="Validation Error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error=ErrorDetail(
            code="validation_error",
            message="Validation failed",
            fields=fields,
        ),
        error_type="https://example.com/problems/validation-error",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _problem(
        request=request,
        title="Internal Server Error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error=ErrorDetail(code="internal_error", message="An unexpected error occurred"),
        error_type="https://example.com/problems/internal-error",
    )
