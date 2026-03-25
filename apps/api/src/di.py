from dataclasses import dataclass
from functools import lru_cache

from src.config import Settings, get_settings


@dataclass(frozen=True)
class Container:
    settings: Settings


@lru_cache(maxsize=1)
def get_container() -> Container:
    return Container(settings=get_settings())
