import os
import secrets
import smtplib
from email.message import EmailMessage

from src.modules.notifications.infrastructure.providers.base import BaseProvider, ProviderSendResult


class EmailProvider(BaseProvider):
    provider_name = "email-smtp"

    def __init__(
        self,
        *,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        sender_email: str | None = None,
        dry_run: bool | None = None,
    ) -> None:
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "1025"))
        self.sender_email = sender_email or os.getenv("SMTP_SENDER", "noreply@eldercare.local")
        self.dry_run = (os.getenv("EMAIL_DRY_RUN", "true").lower() == "true") if dry_run is None else dry_run

    def send(self, recipient_id: str, message: str, metadata: dict[str, str] | None = None) -> ProviderSendResult:
        metadata = metadata or {}
        subject = metadata.get("subject", "Eldercare Notification")
        recipient_email = metadata.get("recipient_email", recipient_id)

        if self.dry_run:
            return ProviderSendResult(
                success=True,
                provider_name=self.provider_name,
                provider_message_id=secrets.token_urlsafe(8),
            )

        email = EmailMessage()
        email["From"] = self.sender_email
        email["To"] = recipient_email
        email["Subject"] = subject
        email.set_content(message)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as client:
                client.send_message(email)
            return ProviderSendResult(
                success=True,
                provider_name=self.provider_name,
                provider_message_id=secrets.token_urlsafe(8),
            )
        except Exception as exc:
            return ProviderSendResult(
                success=False,
                provider_name=self.provider_name,
                error_message=str(exc),
            )
