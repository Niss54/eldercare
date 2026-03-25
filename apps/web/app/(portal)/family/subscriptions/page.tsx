"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "../../../../lib/api-client";
import { webEnv } from "../../../../lib/env";
import { useApiClient } from "../../../../hooks/use-api-client";
import { useAuth } from "../../../../providers/auth-provider";

type Plan = {
  code: "free" | "plus" | "clinical";
  name: string;
  price_monthly_cents: number;
  trial_days: number;
  grace_days: number;
  features: Record<string, boolean>;
};

type SubscriptionState = {
  user_id: string;
  tenant_id: string;
  plan_code: "free" | "plus" | "clinical";
  status: string;
  updated_at: string;
  period_end_at: string | null;
  trial_ends_at: string | null;
  grace_ends_at: string | null;
};

type CheckoutSession = {
  provider: string;
  session_id: string;
  checkout_url: string;
  customer_reference: string;
  plan_reference: string;
  created_at: string;
  metadata?: Record<string, string>;
};

type RazorpayCheckoutResult = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

const loadRazorpayScript = async (): Promise<boolean> => {
  if (typeof window === "undefined") {
    return false;
  }
  if ((window as Window & { Razorpay?: unknown }).Razorpay) {
    return true;
  }
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

export default function FamilySubscriptionsPage() {
  const { session } = useAuth();
  const apiClient = useApiClient();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionState | null>(null);
  const [entitlements, setEntitlements] = useState<Record<string, boolean>>({});
  const [checkoutBusyPlan, setCheckoutBusyPlan] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const paymentProvider = useMemo(() => (webEnv.razorpayKeyId ? "razorpay" : "demo"), []);

  const loadSubscriptionData = useCallback(async () => {
    if (!apiClient.accessToken) {
      setError("Please sign in again to load subscription details.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setInfo(null);

    try {
      const [plansPayload, mePayload, entitlementsPayload] = await Promise.all([
        apiClient.request<{ items?: Plan[] }>("/api/v1/subscriptions/plans", { method: "GET", cache: "no-store" }),
        apiClient.request<SubscriptionState>("/api/v1/subscriptions/me", { method: "GET", cache: "no-store" }),
        apiClient.request<{ items?: Record<string, boolean> }>("/api/v1/subscriptions/entitlements", {
          method: "GET",
          cache: "no-store",
        }),
      ]);

      setPlans(Array.isArray(plansPayload.items) ? (plansPayload.items as Plan[]) : []);
      setSubscription(mePayload as SubscriptionState);
      setEntitlements(
        entitlementsPayload && typeof entitlementsPayload.items === "object" && entitlementsPayload.items !== null
          ? (entitlementsPayload.items as Record<string, boolean>)
          : {},
      );
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while loading subscription details."));
    } finally {
      setIsLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    void loadSubscriptionData();
  }, [loadSubscriptionData]);

  const verifyRazorpayPayment = async (result: RazorpayCheckoutResult) => {
    await apiClient.request("/api/v1/subscriptions/checkout/verify", {
      method: "POST",
      body: result,
    });
    setInfo("Payment successful. Subscription updated.");
    await loadSubscriptionData();
  };

  const startCheckout = async (planCode: Plan["code"]) => {
    if (!apiClient.accessToken) {
      setError("Please sign in again to continue checkout.");
      return;
    }

    setCheckoutBusyPlan(planCode);
    setError(null);
    setInfo(null);

    try {
      const sessionPayload = await apiClient.request<CheckoutSession>("/api/v1/subscriptions/checkout", {
        method: "POST",
        body: { plan_code: planCode, provider: paymentProvider },
      });

      if (sessionPayload.provider === "razorpay") {
        const sdkLoaded = await loadRazorpayScript();
        if (!sdkLoaded) {
          throw new Error("Unable to load Razorpay SDK");
        }

        const razorpayKey = sessionPayload.metadata?.razorpay_key_id || webEnv.razorpayKeyId;
        const orderId = sessionPayload.metadata?.razorpay_order_id || sessionPayload.session_id;
        const amount = Number(sessionPayload.metadata?.amount_cents || "0");
        const currency = sessionPayload.metadata?.currency || "INR";
        if (!razorpayKey || !orderId || amount <= 0) {
          throw new Error("Razorpay checkout payload is incomplete");
        }

        const RazorpayCtor = (window as Window & { Razorpay?: new (options: Record<string, unknown>) => { open: () => void } }).Razorpay;
        if (!RazorpayCtor) {
          throw new Error("Razorpay SDK unavailable after load");
        }

        const razorpay = new RazorpayCtor({
          key: razorpayKey,
          amount,
          currency,
          name: "Eldercare",
          description: `${planCode.toUpperCase()} plan subscription`,
          order_id: orderId,
          prefill: {
            email: session?.username || email,
          },
          notes: {
            customer_reference: sessionPayload.customer_reference,
            plan_reference: sessionPayload.plan_reference,
          },
          handler: async (response: RazorpayCheckoutResult) => {
            try {
              await verifyRazorpayPayment(response);
            } catch (verifyError) {
              setError(getApiErrorMessage(verifyError, "Payment captured but verification failed."));
            }
          },
          theme: {
            color: "#0f766e",
          },
        });
        razorpay.open();
        setInfo("Razorpay checkout opened.");
      } else if (sessionPayload.checkout_url) {
        setInfo(`Checkout session ready: ${sessionPayload.session_id}`);
        window.open(sessionPayload.checkout_url, "_blank", "noopener,noreferrer");
      } else {
        setInfo(`Checkout session ready: ${sessionPayload.session_id}`);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while starting checkout."));
    } finally {
      setCheckoutBusyPlan(null);
    }
  };

  const billingPortalEnabled = Boolean(entitlements["billing.portal"]);

  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Plans and Entitlements</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Live plans, active subscription state, entitlements, and checkout sessions.</p>
        <p style={{ color: "var(--ink-subtle)", marginTop: 0 }}>
          Payment provider: <strong>{paymentProvider === "razorpay" ? "Razorpay" : "Demo (set NEXT_PUBLIC_RAZORPAY_KEY_ID to enable Razorpay)"}</strong>
        </p>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" className="button ghost" onClick={() => void loadSubscriptionData()} disabled={isLoading}>
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {error ? <p style={{ marginTop: "0.7rem", color: "var(--danger, #b42318)" }}>{error}</p> : null}
        {info ? <p style={{ marginTop: "0.7rem", color: "var(--ok, #067647)" }}>{info}</p> : null}
      </article>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
        {plans.map((plan) => (
          <article key={plan.code} className="card" style={{ padding: "0.9rem" }}>
            <h2 style={{ marginTop: 0 }}>{plan.name}</h2>
            <p style={{ fontWeight: 700, margin: "0.4rem 0" }}>
              {plan.price_monthly_cents === 0 ? "Free" : `$${(plan.price_monthly_cents / 100).toFixed(0)}/mo`}
            </p>
            <p style={{ color: "var(--ink-subtle)", minHeight: "2.2rem" }}>
              Trial {plan.trial_days}d · Grace {plan.grace_days}d
            </p>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.7rem" }}>
              {Object.entries(plan.features)
                .filter(([, enabled]) => enabled)
                .slice(0, 4)
                .map(([feature]) => (
                  <span key={feature} className="pill">{feature}</span>
                ))}
            </div>
            <button
              type="button"
              className="button"
              onClick={() => void startCheckout(plan.code)}
              disabled={checkoutBusyPlan === plan.code || plan.code === "free"}
            >
              {checkoutBusyPlan === plan.code ? "Starting..." : plan.code === "free" ? "Included" : "Start checkout"}
            </button>
          </article>
        ))}
      </div>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Current Subscription and Entitlements</h2>
        {subscription ? (
          <div className="card" style={{ padding: "0.7rem", marginBottom: "0.7rem" }}>
            <p style={{ margin: 0 }}>
              <strong>Plan:</strong> {subscription.plan_code}
            </p>
            <p style={{ margin: "0.35rem 0 0" }}>
              <strong>Status:</strong> {subscription.status}
            </p>
          </div>
        ) : null}
        <p style={{ color: "var(--ink-subtle)", marginTop: 0 }}>
          Billing portal access: {billingPortalEnabled ? "enabled" : "upgrade required"}
        </p>
        <div className="grid">
          {Object.keys(entitlements).length === 0 ? (
            <p style={{ color: "var(--ink-subtle)" }}>No entitlements returned.</p>
          ) : null}
          {Object.entries(entitlements).map(([key, enabled]) => (
            <div key={key} className="card" style={{ padding: "0.7rem", display: "flex", justifyContent: "space-between" }}>
              <span>{key}</span>
              <span className="pill">{enabled ? "Enabled" : "Disabled"}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
