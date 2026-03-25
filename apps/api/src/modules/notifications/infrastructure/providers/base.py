from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class ProviderSendResult:
    success: bool
    provider_name: str
    provider_message_id: str | None = None
    error_message: str | None = None


class BaseProvider(ABC):
    provider_name: str

    @abstractmethod
    def send(self, recipient_id: str, message: str, metadata: dict[str, str] | None = None) -> ProviderSendResult:
        raise NotImplementedError
