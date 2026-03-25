from typing import Any


def success_response(
    data: Any,
    *,
    message: str = "ok",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "data": data,
        "meta": meta or {},
    }


def list_response(
    items: list[Any],
    *,
    page: int,
    page_size: int,
    total: int,
    message: str = "ok",
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "count": len(items),
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    if filters:
        meta["filters"] = filters
    return success_response(data={"items": items}, message=message, meta=meta)
