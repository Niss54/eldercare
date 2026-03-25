from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Entity:
    id: str


@dataclass(slots=True)
class Command:
    idempotency_key: str | None = None


@dataclass(slots=True)
class Query:
    pass


@dataclass(slots=True)
class Page:
    items: list[Any]
    total: int
    page: int
    page_size: int


def paginate(items: list[Any], page: int = 1, page_size: int = 20) -> Page:
    safe_page = max(page, 1)
    safe_size = max(page_size, 1)
    start = (safe_page - 1) * safe_size
    end = start + safe_size
    return Page(items=items[start:end], total=len(items), page=safe_page, page_size=safe_size)


@dataclass
class IdempotencyStore:
    seen_keys: set[str] = field(default_factory=set)

    def check_and_set(self, key: str) -> bool:
        if key in self.seen_keys:
            return False
        self.seen_keys.add(key)
        return True


class HandlerRegistry:
    def __init__(self):
        self._handlers: dict[type, Callable[..., Any]] = {}

    def register(self, message_type: type, handler: Callable[..., Any]) -> None:
        self._handlers[message_type] = handler

    def handle(self, message: Any) -> Any:
        message_type = type(message)
        handler = self._handlers.get(message_type)
        if not handler:
            raise ValueError(f"No handler registered for {message_type.__name__}")
        return handler(message)
