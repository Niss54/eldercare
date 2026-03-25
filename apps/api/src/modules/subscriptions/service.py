from datetime import UTC, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field
from src.core.settings import get_settings

from src.modules.audit_logging.store import AuditCategory, AuditOutcome, AuditSeverity, audit_log_store
from src.modules.subscriptions.providers import DemoPaymentProvider, PaymentProviderAdapter, PaymentProviderEvent, RazorpayPaymentProvider


class PlanCode(str, Enum):
    free = "free"
    plus = "plus"
    clinical = "clinical"


class SubscriptionStatus(str, Enum):
    trialing = "trialing"
    active = "active"
    grace_period = "grace_period"
    past_due = "past_due"
    cancelled = "cancelled"
    churned = "churned"


class Plan(BaseModel):
    code: PlanCode
    name: str
    price_monthly_cents: int
    trial_days: int = 14
    grace_days: int = 7
    features: dict[str, bool]


class SubscriptionState(BaseModel):
    user_id: str
    tenant_id: str = "default"
    plan_code: PlanCode
    status: SubscriptionStatus = SubscriptionStatus.active
    payment_provider: str = "demo"
    period_start_at: datetime | None = None
    period_end_at: datetime | None = None
    trial_ends_at: datetime | None = None
    grace_ends_at: datetime | None = None
    dunning_attempts: int = 0
    auto_renew: bool = True
    cancelled_at: datetime | None = None
    updated_at: datetime


class InvoiceStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    void = "void"


class InvoiceRecord(BaseModel):
    id: str
    user_id: str
    tenant_id: str
    plan_code: PlanCode
    amount_cents: int
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.pending
    provider: str = "demo"
    issued_at: datetime
    paid_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class ConversionEvent(BaseModel):
    id: str
    user_id: str
    from_plan: PlanCode
    to_plan: PlanCode
    event_type: str
    occurred_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class SubscriptionService:
    def __init__(self):
        settings = get_settings()
        self.plans: dict[PlanCode, Plan] = {
            PlanCode.free: Plan(
                code=PlanCode.free,
                name="Free",
                price_monthly_cents=0,
                trial_days=0,
                grace_days=0,
                features={
                    "marketplace.booking": False,
                    "advanced.analytics": False,
                    "billing.portal": False,
                    "sos.premium_cascade": False,
                },
            ),
            PlanCode.plus: Plan(
                code=PlanCode.plus,
                name="Plus",
                price_monthly_cents=7900,
                trial_days=14,
                grace_days=7,
                features={
                    "marketplace.booking": True,
                    "advanced.analytics": True,
                    "billing.portal": True,
                    "sos.premium_cascade": True,
                },
            ),
            PlanCode.clinical: Plan(
                code=PlanCode.clinical,
                name="Clinical",
                price_monthly_cents=12900,
                trial_days=21,
                grace_days=10,
                features={
                    "marketplace.booking": True,
                    "advanced.analytics": True,
                    "billing.portal": True,
                    "sos.premium_cascade": True,
                    "doctor.collaboration": True,
                },
            ),
        }
        self.subscriptions: dict[str, SubscriptionState] = {}
        self.invoices: dict[str, InvoiceRecord] = {}
        self.payment_events: dict[str, PaymentProviderEvent] = {}
        self.conversion_events: list[ConversionEvent] = []
        self.pending_checkout: dict[str, dict[str, str]] = {}
        self.providers: dict[str, PaymentProviderAdapter] = {
            "demo": DemoPaymentProvider(),
        }
        if settings.razorpay_key_id and settings.razorpay_key_secret:
            self.providers["razorpay"] = RazorpayPaymentProvider(
                key_id=settings.razorpay_key_id,
                key_secret=settings.razorpay_key_secret,
            )

    def plan_feature_matrix(self) -> dict[str, dict[str, bool]]:
        return {plan.code.value: plan.features for plan in self.plans.values()}

    def list_plans(self) -> list[Plan]:
        return list(self.plans.values())

    def _append_conversion_event(self, user_id: str, from_plan: PlanCode, to_plan: PlanCode, event_type: str, metadata: dict[str, str] | None = None) -> None:
        event = ConversionEvent(
            id=f"conv_{len(self.conversion_events) + 1}",
            user_id=user_id,
            from_plan=from_plan,
            to_plan=to_plan,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            metadata=metadata or {},
        )
        self.conversion_events.append(event)

    def _record_audit(self, actor_user_id: str, action: str, resource_id: str, metadata: dict[str, str]) -> None:
        audit_log_store.append_event(
            actor_user_id=actor_user_id,
            action=action,
            resource_type="subscription",
            resource_id=resource_id,
            event_type="domain.subscription.event",
            category=AuditCategory.operational,
            severity=AuditSeverity.info,
            outcome=AuditOutcome.success,
            domain="subscription",
            metadata=metadata,
        )

    def set_plan(
        self,
        user_id: str,
        plan_code: PlanCode,
        actor_user_id: str | None = None,
        tenant_id: str = "default",
        start_trial: bool = False,
    ) -> SubscriptionState:
        now = datetime.now(UTC)
        previous = self.subscriptions.get(user_id)
        previous_plan = previous.plan_code if previous else PlanCode.free
        plan = self.plans[plan_code]
        status = SubscriptionStatus.active
        trial_ends_at = None
        if start_trial and plan.trial_days > 0 and plan.price_monthly_cents > 0:
            status = SubscriptionStatus.trialing
            trial_ends_at = now + timedelta(days=plan.trial_days)

        state = SubscriptionState(
            user_id=user_id,
            tenant_id=tenant_id,
            plan_code=plan_code,
            status=status,
            payment_provider="demo",
            period_start_at=now,
            period_end_at=now + timedelta(days=30),
            trial_ends_at=trial_ends_at,
            updated_at=now,
        )
        self.subscriptions[user_id] = state

        if previous_plan != plan_code:
            event_type = "conversion" if previous_plan == PlanCode.free and plan_code != PlanCode.free else "plan_change"
            if previous_plan != PlanCode.free and plan_code == PlanCode.free:
                event_type = "churn"
                state.status = SubscriptionStatus.churned
                state.cancelled_at = now
            self._append_conversion_event(
                user_id=user_id,
                from_plan=previous_plan,
                to_plan=plan_code,
                event_type=event_type,
            )

        self._record_audit(
            actor_user_id=actor_user_id or user_id,
            action="subscription.plan.set",
            resource_id=user_id,
            metadata={"plan_code": plan_code.value, "status": state.status.value},
        )
        return state

    def get_subscription(self, user_id: str) -> SubscriptionState:
        existing = self.subscriptions.get(user_id)
        if existing:
            return existing
        state = SubscriptionState(
            user_id=user_id,
            plan_code=PlanCode.free,
            status=SubscriptionStatus.active,
            period_start_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.subscriptions[user_id] = state
        return state

    def list_entitlements(self, user_id: str) -> dict[str, bool]:
        state = self.get_subscription(user_id)
        plan = self.plans[state.plan_code]
        return plan.features

    def has_entitlement(self, user_id: str, feature: str) -> bool:
        state = self.get_subscription(user_id)
        if state.status not in {SubscriptionStatus.active, SubscriptionStatus.trialing, SubscriptionStatus.grace_period}:
            return False
        plan = self.plans[state.plan_code]
        return bool(plan.features.get(feature, False))

    def create_checkout_session(self, user_id: str, plan_code: PlanCode, provider: str = "demo") -> dict[str, str]:
        adapter = self.providers.get(provider)
        if not adapter:
            if provider == "razorpay":
                raise ValueError("razorpay provider not configured on backend")
            raise ValueError("provider not supported")
        plan = self.plans[plan_code]
        session = adapter.create_checkout_session(
            customer_reference=user_id,
            plan_reference=plan_code.value,
            amount_cents=plan.price_monthly_cents,
            currency="INR",
        )
        self.pending_checkout[session.session_id] = {
            "user_id": user_id,
            "plan_code": plan_code.value,
            "amount_cents": str(plan.price_monthly_cents),
            "provider": provider,
        }
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.checkout.created",
            resource_id=session.session_id,
            metadata={"provider": provider, "plan_code": plan_code.value},
        )
        return session.model_dump()

    def verify_razorpay_payment(self, user_id: str, order_id: str, payment_id: str, signature: str) -> dict[str, str]:
        adapter = self.providers.get("razorpay")
        if not isinstance(adapter, RazorpayPaymentProvider):
            raise ValueError("razorpay provider not configured")

        pending = self.pending_checkout.get(order_id)
        if not pending:
            raise ValueError("checkout session not found")
        if pending.get("user_id") != user_id:
            raise ValueError("checkout session does not belong to current user")

        valid = adapter.verify_payment_signature(order_id=order_id, payment_id=payment_id, signature=signature)
        if not valid:
            raise ValueError("invalid Razorpay signature")

        plan_code = PlanCode(pending["plan_code"])
        amount_cents = int(pending["amount_cents"])
        invoice = self.issue_invoice(user_id=user_id, amount_cents=amount_cents, provider="razorpay", currency="INR")
        invoice.status = InvoiceStatus.paid
        invoice.paid_at = datetime.now(UTC)

        self.set_plan(user_id=user_id, plan_code=plan_code, actor_user_id=user_id, start_trial=False)
        self.ingest_payment_event(
            provider="razorpay",
            event_type="payment.succeeded",
            user_id=user_id,
            invoice_id=invoice.id,
            amount_cents=amount_cents,
            status="captured",
            metadata={"order_id": order_id, "payment_id": payment_id},
        )

        self.pending_checkout.pop(order_id, None)
        return {
            "status": "verified",
            "order_id": order_id,
            "payment_id": payment_id,
            "plan_code": plan_code.value,
            "invoice_id": invoice.id,
        }

    def mark_past_due(self, user_id: str) -> SubscriptionState:
        state = self.get_subscription(user_id)
        state.status = SubscriptionStatus.past_due
        state.updated_at = datetime.now(UTC)
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.past_due",
            resource_id=user_id,
            metadata={"plan_code": state.plan_code.value},
        )
        return state

    def start_grace_period(self, user_id: str) -> SubscriptionState:
        state = self.get_subscription(user_id)
        plan = self.plans[state.plan_code]
        state.status = SubscriptionStatus.grace_period
        state.grace_ends_at = datetime.now(UTC) + timedelta(days=max(1, plan.grace_days))
        state.updated_at = datetime.now(UTC)
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.grace_started",
            resource_id=user_id,
            metadata={"grace_days": str(plan.grace_days)},
        )
        return state

    def process_dunning_attempt(self, user_id: str) -> SubscriptionState:
        state = self.get_subscription(user_id)
        state.dunning_attempts += 1
        state.updated_at = datetime.now(UTC)
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.dunning_attempt",
            resource_id=user_id,
            metadata={"attempt": str(state.dunning_attempts)},
        )
        return state

    def renew_subscription(self, user_id: str) -> SubscriptionState:
        state = self.get_subscription(user_id)
        now = datetime.now(UTC)
        state.status = SubscriptionStatus.active
        state.period_start_at = now
        state.period_end_at = now + timedelta(days=30)
        state.grace_ends_at = None
        state.dunning_attempts = 0
        state.updated_at = now
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.renewed",
            resource_id=user_id,
            metadata={"plan_code": state.plan_code.value},
        )
        return state

    def cancel_subscription(self, user_id: str) -> SubscriptionState:
        state = self.get_subscription(user_id)
        now = datetime.now(UTC)
        previous_plan = state.plan_code
        state.status = SubscriptionStatus.cancelled
        state.cancelled_at = now
        state.updated_at = now
        self._append_conversion_event(
            user_id=user_id,
            from_plan=previous_plan,
            to_plan=PlanCode.free,
            event_type="churn",
        )
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.cancelled",
            resource_id=user_id,
            metadata={"plan_code": state.plan_code.value},
        )
        return state

    def issue_invoice(self, user_id: str, amount_cents: int, provider: str = "demo", currency: str = "USD") -> InvoiceRecord:
        state = self.get_subscription(user_id)
        invoice = InvoiceRecord(
            id=f"inv_{len(self.invoices) + 1}",
            user_id=user_id,
            tenant_id=state.tenant_id,
            plan_code=state.plan_code,
            amount_cents=amount_cents,
            currency=currency,
            provider=provider,
            issued_at=datetime.now(UTC),
        )
        self.invoices[invoice.id] = invoice
        self._record_audit(
            actor_user_id=user_id,
            action="subscription.invoice.issued",
            resource_id=invoice.id,
            metadata={"amount_cents": str(amount_cents), "provider": provider},
        )
        return invoice

    def ingest_payment_event(
        self,
        provider: str,
        event_type: str,
        user_id: str,
        invoice_id: str | None = None,
        amount_cents: int | None = None,
        status: str = "received",
        metadata: dict[str, str] | None = None,
    ) -> PaymentProviderEvent:
        adapter = self.providers.get(provider)
        if not adapter:
            raise ValueError("provider not supported")

        event = adapter.normalize_event(
            event_type=event_type,
            customer_reference=user_id,
            invoice_id=invoice_id,
            amount_cents=amount_cents,
            status=status,
            metadata=metadata,
        )
        self.payment_events[event.event_id] = event

        if invoice_id and invoice_id in self.invoices:
            invoice = self.invoices[invoice_id]
            if event_type in {"invoice.paid", "payment.succeeded"}:
                invoice.status = InvoiceStatus.paid
                invoice.paid_at = datetime.now(UTC)
                self.renew_subscription(user_id)
            elif event_type in {"invoice.failed", "payment.failed"}:
                invoice.status = InvoiceStatus.failed
                self.mark_past_due(user_id)
                self.start_grace_period(user_id)
                self.process_dunning_attempt(user_id)

        self._record_audit(
            actor_user_id=user_id,
            action="subscription.payment_event.ingested",
            resource_id=event.event_id,
            metadata={"provider": provider, "event_type": event_type, "status": status},
        )
        return event

    def list_invoices(self, user_id: str | None = None) -> list[InvoiceRecord]:
        items = list(self.invoices.values())
        if user_id:
            items = [item for item in items if item.user_id == user_id]
        return sorted(items, key=lambda item: item.issued_at, reverse=True)

    def list_payment_events(self, user_id: str | None = None) -> list[PaymentProviderEvent]:
        items = list(self.payment_events.values())
        if user_id:
            items = [item for item in items if item.customer_reference == user_id]
        return sorted(items, key=lambda item: item.received_at, reverse=True)

    def conversion_and_churn_metrics(self) -> dict[str, object]:
        conversions = [event for event in self.conversion_events if event.event_type in {"conversion", "plan_change"}]
        churn = [event for event in self.conversion_events if event.event_type == "churn"]
        by_plan: dict[str, int] = {}
        for sub in self.subscriptions.values():
            by_plan[sub.plan_code.value] = by_plan.get(sub.plan_code.value, 0) + 1
        return {
            "conversion_events": len(conversions),
            "churn_events": len(churn),
            "active_by_plan": by_plan,
            "payment_events": len(self.payment_events),
            "invoices_total": len(self.invoices),
        }


subscription_service = SubscriptionService()
