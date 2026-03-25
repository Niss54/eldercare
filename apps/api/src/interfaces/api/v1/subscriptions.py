from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.modules.subscriptions.service import PlanCode, subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SetPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    plan_code: PlanCode
    tenant_id: str = "default"
    start_trial: bool = False


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: PlanCode
    provider: str = "razorpay"


class RazorpayVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class RazorpayWebhookRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    event: str
    payload: dict


class PaymentEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "demo"
    event_type: str
    user_id: str
    invoice_id: str | None = None
    amount_cents: int | None = None
    status: str = "received"
    metadata: dict[str, str] = Field(default_factory=dict)


class LifecycleUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str


class InvoiceIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    amount_cents: int = Field(ge=0)
    provider: str = "demo"
    currency: str = "USD"


@router.get("/plans")
def list_plans(claims: dict = Depends(_get_claims)):
    if "subscription:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: subscription:read")
    plans = subscription_service.list_plans()
    return {"count": len(plans), "items": [p.model_dump() for p in plans]}


@router.get("/matrix")
def plan_feature_matrix(claims: dict = Depends(_get_claims)):
    if "subscription:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: subscription:read")
    matrix = subscription_service.plan_feature_matrix()
    return {"count": len(matrix), "items": matrix}


@router.get("/me")
def my_subscription(claims: dict = Depends(_get_claims)):
    if "subscription:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: subscription:read")
    return subscription_service.get_subscription(claims["sub"]).model_dump()


@router.get("/entitlements")
def my_entitlements(claims: dict = Depends(_get_claims)):
    if "subscription:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: subscription:read")
    return {
        "user_id": claims["sub"],
        "items": subscription_service.list_entitlements(claims["sub"]),
    }


@router.post("/set-plan")
def set_plan(payload: SetPlanRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    state = subscription_service.set_plan(
        user_id=payload.user_id,
        plan_code=payload.plan_code,
        actor_user_id=claims["sub"],
        tenant_id=payload.tenant_id,
        start_trial=payload.start_trial,
    )
    return state.model_dump()


@router.post("/checkout")
def create_checkout(payload: CheckoutRequest, claims: dict = Depends(_get_claims)):
    if "subscription:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: subscription:read")
    try:
        session = subscription_service.create_checkout_session(
            user_id=claims["sub"],
            plan_code=payload.plan_code,
            provider=payload.provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return session


@router.post("/checkout/verify")
def verify_checkout(payload: RazorpayVerifyRequest, claims: dict = Depends(_get_claims)):
    if "subscription:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: subscription:read")
    try:
        result = subscription_service.verify_razorpay_payment(
            user_id=claims["sub"],
            order_id=payload.razorpay_order_id,
            payment_id=payload.razorpay_payment_id,
            signature=payload.razorpay_signature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/payments/razorpay/webhook")
def razorpay_webhook(payload: RazorpayWebhookRequest):
    # Webhook signature verification should be enforced at ingress/API gateway in non-local envs.
    event = payload.event
    body = payload.payload or {}
    payment_entity = (((body.get("payment") or {}).get("entity")) if isinstance(body, dict) else None) or {}
    notes = payment_entity.get("notes") if isinstance(payment_entity, dict) else {}
    customer_reference = notes.get("customer_reference") if isinstance(notes, dict) else None
    if not customer_reference:
        return {"status": "ignored", "reason": "missing customer_reference"}

    amount = payment_entity.get("amount") if isinstance(payment_entity, dict) else None
    payment_id = payment_entity.get("id") if isinstance(payment_entity, dict) else None
    order_id = payment_entity.get("order_id") if isinstance(payment_entity, dict) else None
    mapped_status = "captured" if event == "payment.captured" else "received"
    mapped_event = "payment.succeeded" if event == "payment.captured" else event

    subscription_service.ingest_payment_event(
        provider="razorpay",
        event_type=mapped_event,
        user_id=customer_reference,
        amount_cents=int(amount) if isinstance(amount, int) else None,
        status=mapped_status,
        metadata={
            "payment_id": str(payment_id or ""),
            "order_id": str(order_id or ""),
        },
    )
    return {"status": "ok"}


@router.get("/entitlements/check")
def check_entitlement(feature: str, claims: dict = Depends(_get_claims)):
    enabled = subscription_service.has_entitlement(user_id=claims["sub"], feature=feature)
    return {"user_id": claims["sub"], "feature": feature, "enabled": enabled}


@router.post("/lifecycle/grace")
def lifecycle_grace(payload: LifecycleUserRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    state = subscription_service.start_grace_period(payload.user_id)
    return state.model_dump()


@router.post("/lifecycle/dunning")
def lifecycle_dunning(payload: LifecycleUserRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    state = subscription_service.process_dunning_attempt(payload.user_id)
    return state.model_dump()


@router.post("/lifecycle/renew")
def lifecycle_renew(payload: LifecycleUserRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    state = subscription_service.renew_subscription(payload.user_id)
    return state.model_dump()


@router.post("/lifecycle/cancel")
def lifecycle_cancel(payload: LifecycleUserRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    state = subscription_service.cancel_subscription(payload.user_id)
    return state.model_dump()


@router.post("/invoices")
def issue_invoice(payload: InvoiceIssueRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    invoice = subscription_service.issue_invoice(
        user_id=payload.user_id,
        amount_cents=payload.amount_cents,
        provider=payload.provider,
        currency=payload.currency,
    )
    return invoice.model_dump()


@router.get("/invoices")
def list_invoices(user_id: str | None = None, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])):
        user_id = claims["sub"]
    invoices = subscription_service.list_invoices(user_id=user_id)
    return {"count": len(invoices), "items": [item.model_dump() for item in invoices]}


@router.post("/payments/events")
def ingest_payment_event(payload: PaymentEventRequest, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])) and claims["sub"] != payload.user_id:
        raise HTTPException(status_code=403, detail="Missing permission: subscription:manage")
    try:
        event = subscription_service.ingest_payment_event(
            provider=payload.provider,
            event_type=payload.event_type,
            user_id=payload.user_id,
            invoice_id=payload.invoice_id,
            amount_cents=payload.amount_cents,
            status=payload.status,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return event.model_dump()


@router.get("/payments/events")
def list_payment_events(user_id: str | None = None, claims: dict = Depends(_get_claims)):
    if "subscription:manage" not in set(claims.get("permissions", [])):
        user_id = claims["sub"]
    items = subscription_service.list_payment_events(user_id=user_id)
    return {"count": len(items), "items": [item.model_dump() for item in items]}


@router.get("/analytics")
def subscription_analytics(claims: dict = Depends(_get_claims)):
    if "analytics:read" not in set(claims.get("permissions", [])):
        raise HTTPException(status_code=403, detail="Missing permission: analytics:read")
    return subscription_service.conversion_and_churn_metrics()
