from datetime import UTC, datetime
import base64
import hashlib
import hmac
import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class CheckoutSession(BaseModel):
    provider: str
    session_id: str
    checkout_url: str
    customer_reference: str
    plan_reference: str
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class PaymentProviderEvent(BaseModel):
    provider: str
    event_id: str
    event_type: str
    customer_reference: str
    invoice_id: str | None = None
    amount_cents: int | None = None
    currency: str = "USD"
    status: str = "received"
    received_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class PaymentProviderAdapter(Protocol):
    provider_name: str

    def create_checkout_session(
        self,
        customer_reference: str,
        plan_reference: str,
        amount_cents: int,
        currency: str = "INR",
    ) -> CheckoutSession:
        ...

    def normalize_event(
        self,
        event_type: str,
        customer_reference: str,
        invoice_id: str | None = None,
        amount_cents: int | None = None,
        status: str = "received",
        metadata: dict[str, str] | None = None,
    ) -> PaymentProviderEvent:
        ...


class DemoPaymentProvider:
    provider_name = "demo"

    def create_checkout_session(
        self,
        customer_reference: str,
        plan_reference: str,
        amount_cents: int,
        currency: str = "INR",
    ) -> CheckoutSession:
        now = datetime.now(UTC)
        session_id = f"chk_{customer_reference}_{int(now.timestamp())}"
        return CheckoutSession(
            provider=self.provider_name,
            session_id=session_id,
            checkout_url=f"https://payments.demo/checkout/{session_id}",
            customer_reference=customer_reference,
            plan_reference=plan_reference,
            created_at=now,
            metadata={"amount_cents": str(amount_cents), "currency": currency},
        )

    def normalize_event(
        self,
        event_type: str,
        customer_reference: str,
        invoice_id: str | None = None,
        amount_cents: int | None = None,
        status: str = "received",
        metadata: dict[str, str] | None = None,
    ) -> PaymentProviderEvent:
        now = datetime.now(UTC)
        event_id = f"evt_{customer_reference}_{event_type}_{int(now.timestamp())}"
        return PaymentProviderEvent(
            provider=self.provider_name,
            event_id=event_id,
            event_type=event_type,
            customer_reference=customer_reference,
            invoice_id=invoice_id,
            amount_cents=amount_cents,
            status=status,
            received_at=now,
            metadata=metadata or {},
        )


class RazorpayPaymentProvider:
    provider_name = "razorpay"

    def __init__(self, key_id: str, key_secret: str):
        self.key_id = key_id
        self.key_secret = key_secret

    def _auth_header(self) -> str:
        raw = f"{self.key_id}:{self.key_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def create_checkout_session(
        self,
        customer_reference: str,
        plan_reference: str,
        amount_cents: int,
        currency: str = "INR",
    ) -> CheckoutSession:
        now = datetime.now(UTC)
        payload = {
            "amount": amount_cents,
            "currency": currency,
            "receipt": f"sub_{customer_reference}_{int(now.timestamp())}",
            "notes": {
                "customer_reference": customer_reference,
                "plan_reference": plan_reference,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url="https://api.razorpay.com/v1/orders",
            data=body,
            method="POST",
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Razorpay order creation failed: {detail or exc.reason}") from exc
        except URLError as exc:
            raise ValueError(f"Razorpay order creation failed: {exc.reason}") from exc

        parsed = json.loads(raw)
        order_id = parsed.get("id")
        if not order_id:
            raise ValueError("Razorpay order creation failed: missing order id")

        return CheckoutSession(
            provider=self.provider_name,
            session_id=order_id,
            checkout_url="",
            customer_reference=customer_reference,
            plan_reference=plan_reference,
            created_at=now,
            metadata={
                "razorpay_key_id": self.key_id,
                "razorpay_order_id": order_id,
                "amount_cents": str(amount_cents),
                "currency": currency,
            },
        )

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        message = f"{order_id}|{payment_id}".encode("utf-8")
        digest = hmac.new(self.key_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)

    def normalize_event(
        self,
        event_type: str,
        customer_reference: str,
        invoice_id: str | None = None,
        amount_cents: int | None = None,
        status: str = "received",
        metadata: dict[str, str] | None = None,
    ) -> PaymentProviderEvent:
        now = datetime.now(UTC)
        event_id = f"rzp_{customer_reference}_{event_type}_{int(now.timestamp())}"
        return PaymentProviderEvent(
            provider=self.provider_name,
            event_id=event_id,
            event_type=event_type,
            customer_reference=customer_reference,
            invoice_id=invoice_id,
            amount_cents=amount_cents,
            currency="INR",
            status=status,
            received_at=now,
            metadata=metadata or {},
        )
