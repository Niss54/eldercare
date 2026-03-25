"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "../../../../lib/api-client";
import { webEnv } from "../../../../lib/env";
import { useApiClient } from "../../../../hooks/use-api-client";
import {
  notificationsSdk,
  type NotificationDelivery as Delivery,
  type NotificationPreference as Preference,
} from "../../../../lib/sdk/notifications";
import { useAuth } from "../../../../providers/auth-provider";

type Toast = {
  id: number;
  title: string;
  message: string;
  tone: "urgent" | "routine";
};

const CHANNELS = ["email", "sms", "push", "in_app"];

const mergeDeliveries = (incoming: Delivery[], existing: Delivery[]) => {
  const dedup = new Map<string, Delivery>();
  for (const item of existing) {
    dedup.set(item.id, item);
  }
  for (const item of incoming) {
    dedup.set(item.id, item);
  }
  return Array.from(dedup.values()).sort((a, b) => b.created_at.localeCompare(a.created_at));
};

const toWsUrl = (baseUrl: string) => {
  if (baseUrl.startsWith("https://")) {
    return `wss://${baseUrl.slice("https://".length)}`;
  }
  if (baseUrl.startsWith("http://")) {
    return `ws://${baseUrl.slice("http://".length)}`;
  }
  return baseUrl;
};

export default function FamilyNotificationsPage() {
  const { session } = useAuth();
  const apiClient = useApiClient();
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [preference, setPreference] = useState<Preference | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingPref, setIsSavingPref] = useState(false);
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((title: string, message: string, tone: "urgent" | "routine") => {
    const toast: Toast = { id: Date.now(), title, message, tone };
    setToasts((previous) => [toast, ...previous].slice(0, 4));
  }, []);

  const loadDeliveries = useCallback(async () => {
    if (!apiClient.accessToken || !session?.userId) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const items = await notificationsSdk.listDeliveries(apiClient.accessToken, session.userId);
      setDeliveries((previous) => mergeDeliveries(items, previous));
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while loading notification history."));
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, session?.userId]);

  const loadPreference = useCallback(async () => {
    if (!apiClient.accessToken || !session?.userId) {
      return;
    }
    try {
      const payload = await notificationsSdk.getPreference(apiClient.accessToken, session.userId);
      setPreference(payload);
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while loading preferences."));
    }
  }, [apiClient, session?.userId]);

  useEffect(() => {
    void loadDeliveries();
    void loadPreference();
  }, [loadDeliveries, loadPreference]);

  useEffect(() => {
    if (!session?.accessToken) {
      return;
    }

    const wsBase = toWsUrl(webEnv.apiBaseUrl);
    const ws = new WebSocket(`${wsBase}/ws/notifications?token=${encodeURIComponent(session.accessToken)}`);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          event_type?: string;
          payload?: { channel?: string; priority?: string; status?: string; delivery_id?: string };
        };

        if (payload.event_type === "ws.connected") {
          return;
        }

        if (payload.event_type === "notification.delivered" || payload.event_type === "notification.failed") {
          const tone = payload.event_type === "notification.failed" ? "urgent" : "routine";
          const channel = payload.payload?.channel ?? "unknown";
          const status = payload.payload?.status ?? "updated";
          const deliveryId = payload.payload?.delivery_id;
          addToast("Realtime notification", `${channel} ${status}`, tone);

          if (deliveryId) {
            setDeliveries((previous) =>
              previous.map((item) => (item.id === deliveryId ? { ...item, status } : item)),
            );
          }
          void loadDeliveries();
        }
      } catch {
        // Ignore malformed websocket payloads.
      }
    };

    ws.onerror = () => {
      addToast("Realtime feed", "Connection issue detected", "urgent");
    };

    return () => {
      ws.close();
    };
  }, [addToast, loadDeliveries, session?.accessToken]);

  const toggleChannel = (channel: string) => {
    setPreference((previous) => {
      if (!previous) {
        return previous;
      }
      const enabled = new Set(previous.enabled_channels);
      if (enabled.has(channel)) {
        enabled.delete(channel);
      } else {
        enabled.add(channel);
      }
      return { ...previous, enabled_channels: Array.from(enabled) };
    });
  };

  const savePreference = async () => {
    if (!apiClient.accessToken || !session?.userId || !preference) {
      return;
    }
    setIsSavingPref(true);
    setError(null);
    setInfo(null);
    try {
      const payload = await notificationsSdk.putPreference(apiClient.accessToken, session.userId, {
        enabled_channels: preference.enabled_channels,
        quiet_hours_start_utc: preference.quiet_hours_start_utc,
        quiet_hours_end_utc: preference.quiet_hours_end_utc,
        locale: preference.locale,
        accessibility_plain_text: preference.accessibility_plain_text,
      });
      setPreference(payload);
      setInfo("Preferences updated.");
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while saving preferences."));
    } finally {
      setIsSavingPref(false);
    }
  };

  const sendTestNotification = async () => {
    if (!apiClient.accessToken || !session?.userId) {
      return;
    }
    setIsSendingTest(true);
    setError(null);
    setInfo(null);

    const optimistic: Delivery = {
      id: `tmp-${Date.now()}`,
      channel: "in_app",
      priority: "routine",
      status: "queued",
      message: `Test ping ${new Date().toISOString()}`,
      created_at: new Date().toISOString(),
      provider_name: "pending",
    };
    setDeliveries((previous) => mergeDeliveries([optimistic], previous));

    try {
      const delivered = await notificationsSdk.sendNotification(apiClient.accessToken, {
        recipient_user_id: session.userId,
        message: optimistic.message,
        channels: ["in_app"],
        priority: "routine",
        mode: "fanout",
      });
      setDeliveries((previous) =>
        mergeDeliveries(
          delivered,
          previous.filter((item) => item.id !== optimistic.id),
        ),
      );
      setInfo("Test notification sent.");
      void loadDeliveries();
    } catch (err) {
      setDeliveries((previous) => previous.filter((item) => item.id !== optimistic.id));
      setError(getApiErrorMessage(err, "Network issue while sending test notification."));
    } finally {
      setIsSendingTest(false);
    }
  };

  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Notifications Center</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Live delivery history, user preferences, and realtime notification feed.</p>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button type="button" className="button ghost" onClick={() => void loadDeliveries()} disabled={isLoading}>
            {isLoading ? "Refreshing..." : "Refresh history"}
          </button>
          <button type="button" className="button" onClick={() => void sendTestNotification()} disabled={isSendingTest}>
            {isSendingTest ? "Sending..." : "Send test notification"}
          </button>
        </div>
        <div aria-live="polite" role="status">
          {error ? <p style={{ marginTop: "0.7rem", color: "var(--danger, #b42318)" }}>{error}</p> : null}
          {info ? <p style={{ marginTop: "0.7rem", color: "var(--ok, #067647)" }}>{info}</p> : null}
        </div>
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Channel Preferences</h2>
        {preference ? (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", alignItems: "end" }}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: "0.35rem" }}>Enabled channels</div>
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                {CHANNELS.map((channel) => {
                  const active = preference.enabled_channels.includes(channel);
                  return (
                    <button
                      key={channel}
                      type="button"
                      className={active ? "button" : "button ghost"}
                      onClick={() => toggleChannel(channel)}
                    >
                      {channel}
                    </button>
                  );
                })}
              </div>
            </div>

            <label>
              Quiet start (UTC)
              <input
                type="number"
                min={0}
                max={23}
                value={preference.quiet_hours_start_utc ?? ""}
                onChange={(e) =>
                  setPreference((previous) =>
                    previous ? { ...previous, quiet_hours_start_utc: e.target.value === "" ? null : Number(e.target.value) } : previous,
                  )
                }
                style={{ width: "100%", marginTop: "0.3rem", padding: "0.45rem", border: "1px solid var(--line)", borderRadius: 10 }}
              />
            </label>

            <label>
              Quiet end (UTC)
              <input
                type="number"
                min={0}
                max={23}
                value={preference.quiet_hours_end_utc ?? ""}
                onChange={(e) =>
                  setPreference((previous) =>
                    previous ? { ...previous, quiet_hours_end_utc: e.target.value === "" ? null : Number(e.target.value) } : previous,
                  )
                }
                style={{ width: "100%", marginTop: "0.3rem", padding: "0.45rem", border: "1px solid var(--line)", borderRadius: 10 }}
              />
            </label>

            <label>
              Locale
              <input
                value={preference.locale}
                onChange={(e) => setPreference((previous) => (previous ? { ...previous, locale: e.target.value } : previous))}
                style={{ width: "100%", marginTop: "0.3rem", padding: "0.45rem", border: "1px solid var(--line)", borderRadius: 10 }}
              />
            </label>

            <label style={{ display: "flex", gap: "0.45rem", alignItems: "center" }}>
              <input
                type="checkbox"
                checked={preference.accessibility_plain_text}
                onChange={(e) =>
                  setPreference((previous) =>
                    previous ? { ...previous, accessibility_plain_text: e.target.checked } : previous,
                  )
                }
              />
              Accessibility plain text
            </label>

            <button type="button" className="button" onClick={() => void savePreference()} disabled={isSavingPref}>
              {isSavingPref ? "Saving..." : "Save preferences"}
            </button>
          </div>
        ) : (
          <p style={{ color: "var(--ink-subtle)" }}>Loading preferences...</p>
        )}
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Delivery History</h2>
        <div className="grid" role="list" aria-label="Notification delivery history">
          {deliveries.length === 0 ? <p style={{ color: "var(--ink-subtle)" }}>No deliveries found yet.</p> : null}
          {deliveries.map((item) => (
            <div key={item.id} className="card" role="listitem" style={{ padding: "0.7rem", display: "flex", justifyContent: "space-between" }}>
              <div>
                <strong>{item.message}</strong>
                <div style={{ color: "var(--ink-subtle)", fontSize: "0.86rem" }}>
                  {item.id} · {item.channel} · {item.provider_name}
                </div>
              </div>
              <span className="pill">{item.priority}/{item.status}</span>
            </div>
          ))}
        </div>
      </article>

      <div style={{ position: "fixed", right: "1rem", bottom: "1rem", display: "grid", gap: "0.55rem", zIndex: 25 }}>
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="card"
            style={{
              padding: "0.7rem",
              width: "min(360px, calc(100vw - 2rem))",
              borderLeft: toast.tone === "urgent" ? "4px solid var(--critical)" : "4px solid var(--primary)",
            }}
          >
            <div style={{ fontSize: "0.78rem", color: "var(--ink-subtle)" }}>{toast.title}</div>
            <div>{toast.message}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
