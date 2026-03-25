import secrets

from src.modules.notifications.infrastructure.providers.base import BaseProvider, ProviderSendResult


class SmsProvider(BaseProvider):
    provider_name = "sms-twilio-stub"

    def send(self, recipient_id: str, message: str, metadata: dict[str, str] | None = None) -> ProviderSendResult:
        if "__force_fail__" in message:
            return ProviderSendResult(
                success=False,
                provider_name=self.provider_name,
                error_message="Simulated provider outage",
            )
        return ProviderSendResult(
            success=True,
            provider_name=self.provider_name,
            provider_message_id=secrets.token_urlsafe(8),
        )
