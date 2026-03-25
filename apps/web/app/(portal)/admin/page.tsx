"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "../../../lib/api-client";
import { useApiClient } from "../../../hooks/use-api-client";
import { useAuth } from "../../../providers/auth-provider";

type DashboardResponse = {
  filters_applied: {
    geography: string | null;
    role: string | null;
    plan: string | null;
    time_window: string | null;
  };
  marketplace: {
    caregivers_total: number;
    caregivers_approved: number;
    bookings_total: number;
  };
  subscriptions: {
    active_subscriptions: number;
    conversion_events: number;
    churn_events: number;
  };
  sos: {
    incidents_total: number;
    incidents_acknowledged: number;
  };
  queue_health: {
    medication_pending: number;
    notification_failures: number;
    sos_open_incidents: number;
  };
  alerts: Array<{ severity: string; message: string }>;
  usage_cards: Array<{ key: string; label: string; value: string }>;
};

type FeatureFlag = {
  key: string;
  enabled: boolean;
  rollout_percentage: number;
  roles: string[];
  plans: string[];
  updated_at: string;
};

const defaultFilters = {
  geography: "all",
  role: "all",
  plan: "all",
  timeWindow: "7d",
};

export default function AdminDashboardPage() {
  const { session } = useAuth();
  const apiClient = useApiClient();
  const [filters, setFilters] = useState(defaultFilters);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([]);

  const [disableUserId, setDisableUserId] = useState("");
  const [disableReason, setDisableReason] = useState("Policy/security violation");
  const [inviteRequestId, setInviteRequestId] = useState("");
  const [incidentId, setIncidentId] = useState("");
  const [incidentDecision, setIncidentDecision] = useState("approved");
  const [incidentNotes, setIncidentNotes] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [updatingFlagKey, setUpdatingFlagKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const loadAdminData = useCallback(async () => {
    if (!apiClient.accessToken) {
      setError("Please sign in again with admin access.");
      return;
    }

    const params = new URLSearchParams();
    if (filters.geography !== "all") params.set("geography", filters.geography);
    if (filters.role !== "all") params.set("role", filters.role);
    if (filters.plan !== "all") params.set("plan", filters.plan);
    if (filters.timeWindow) params.set("time_window", filters.timeWindow);

    setIsLoading(true);
    setError(null);
    setInfo(null);

    try {
      const [dashboardPayload, flagsPayload] = await Promise.all([
        apiClient.request<DashboardResponse>(`/api/v1/admin-analytics/dashboard?${params.toString()}`, {
          method: "GET",
          cache: "no-store",
        }),
        apiClient.request<{ items?: FeatureFlag[] }>("/api/v1/admin-analytics/feature-flags", {
          method: "GET",
          cache: "no-store",
        }),
      ]);

      setDashboard(dashboardPayload as DashboardResponse);
      setFeatureFlags(Array.isArray(flagsPayload.items) ? (flagsPayload.items as FeatureFlag[]) : []);
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while loading admin dashboard."));
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, filters.geography, filters.plan, filters.role, filters.timeWindow]);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

  const runAction = async (action: "disable-account" | "resend-invite" | "incident-review") => {
    if (!apiClient.accessToken) {
      setError("Please sign in again with admin access.");
      return;
    }

    setBusyAction(action);
    setError(null);
    setInfo(null);

    let path = "";
    let body: Record<string, string | null> = {};

    if (action === "disable-account") {
      path = "disable-account";
      body = { user_id: disableUserId.trim(), reason: disableReason.trim() };
    }
    if (action === "resend-invite") {
      path = "resend-invite";
      body = { request_id: inviteRequestId.trim() || null };
    }
    if (action === "incident-review") {
      path = "incident-review";
      body = {
        incident_id: incidentId.trim(),
        decision: incidentDecision.trim(),
        notes: incidentNotes.trim() || null,
      };
    }

    try {
      const payload = await apiClient.request<{ action: string; detail: string }>(`/api/v1/admin-analytics/actions/${path}`, {
        method: "POST",
        body,
      });
      setInfo(`${payload.action}: ${payload.detail}`);
      void loadAdminData();
    } catch (err) {
      setError(getApiErrorMessage(err, `Network issue while running ${action}.`));
    } finally {
      setBusyAction(null);
    }
  };

  const exportReport = async (format: "csv" | "json") => {
    if (!apiClient.accessToken) {
      setError("Please sign in again with admin access.");
      return;
    }

    setBusyAction(`export-${format}`);
    setError(null);
    setInfo(null);

    try {
      const params = new URLSearchParams();
      params.set("format", format);
      if (filters.geography !== "all") params.set("geography", filters.geography);
      if (filters.role !== "all") params.set("role", filters.role);
      if (filters.plan !== "all") params.set("plan", filters.plan);
      if (filters.timeWindow) params.set("time_window", filters.timeWindow);

      const blob = await apiClient.request<Blob>(`/api/v1/admin-analytics/reports/export?${params.toString()}`, {
        method: "GET",
        parseAs: "blob",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `admin-report.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setInfo(`Exported ${format.toUpperCase()} report.`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while exporting report."));
    } finally {
      setBusyAction(null);
    }
  };

  const updateFeatureFlag = async (flag: FeatureFlag) => {
    if (!apiClient.accessToken) {
      setError("Please sign in again with admin access.");
      return;
    }

    setUpdatingFlagKey(flag.key);
    setError(null);
    setInfo(null);

    try {
      await apiClient.request(`/api/v1/admin-analytics/feature-flags/${encodeURIComponent(flag.key)}`, {
        method: "POST",
        body: {
          enabled: flag.enabled,
          rollout_percentage: flag.rollout_percentage,
          roles: flag.roles,
          plans: flag.plans,
        },
      });
      setInfo(`Feature flag updated: ${flag.key}`);
      void loadAdminData();
    } catch (err) {
      setError(getApiErrorMessage(err, `Network issue while updating ${flag.key}.`));
    } finally {
      setUpdatingFlagKey(null);
    }
  };

  const updateLocalFlag = (key: string, updates: Partial<FeatureFlag>) => {
    setFeatureFlags((previous) => previous.map((flag) => (flag.key === key ? { ...flag, ...updates } : flag)));
  };

  const summaryCards = dashboard
    ? [
        {
          key: "usage",
          label: "Usage",
          value: `${dashboard.marketplace.caregivers_total} caregivers`,
          sub: `${dashboard.marketplace.bookings_total} bookings`,
        },
        {
          key: "incidents",
          label: "Incidents",
          value: `${dashboard.sos.incidents_total} SOS incidents`,
          sub: `${dashboard.sos.incidents_acknowledged} acknowledged`,
        },
        {
          key: "alerts",
          label: "Alerts",
          value: `${dashboard.alerts.length} alerts`,
          sub: dashboard.alerts[0]?.message ?? "No active alerts",
        },
        {
          key: "queue",
          label: "Queue Health",
          value: `${dashboard.queue_health.medication_pending} medication pending`,
          sub: `${dashboard.queue_health.notification_failures} notification failures`,
        },
      ]
    : [];

  return (
    <section className="grid" style={{ gap: "1rem" }}>
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Admin Analytics and Operations</h1>
        <p style={{ color: "var(--ink-subtle)", marginBottom: "0.9rem" }}>
          Monitor usage, incidents, alerts, and queue health with admin-only controls for operational response.
        </p>
        <form style={{ display: "grid", gap: "0.6rem", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
          <label style={{ display: "grid", gap: "0.35rem", fontSize: "0.9rem" }}>
            Geography
            <select value={filters.geography} onChange={(e) => setFilters((previous) => ({ ...previous, geography: e.target.value }))}>
              <option value="all">All</option>
              <option value="bangalore">Bangalore</option>
              <option value="delhi">Delhi</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: "0.35rem", fontSize: "0.9rem" }}>
            Role
            <select value={filters.role} onChange={(e) => setFilters((previous) => ({ ...previous, role: e.target.value }))}>
              <option value="all">All</option>
              <option value="admin">Admin</option>
              <option value="family_member">Family Member</option>
              <option value="caregiver">Caregiver</option>
              <option value="doctor">Doctor</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: "0.35rem", fontSize: "0.9rem" }}>
            Plan
            <select value={filters.plan} onChange={(e) => setFilters((previous) => ({ ...previous, plan: e.target.value }))}>
              <option value="all">All</option>
              <option value="free">Free</option>
              <option value="plus">Plus</option>
              <option value="clinical">Clinical</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: "0.35rem", fontSize: "0.9rem" }}>
            Time Window
            <select value={filters.timeWindow} onChange={(e) => setFilters((previous) => ({ ...previous, timeWindow: e.target.value }))}>
              <option value="24h">24h</option>
              <option value="7d">7d</option>
              <option value="30d">30d</option>
            </select>
          </label>
          <button type="button" className="button" onClick={() => void loadAdminData()} disabled={isLoading}>
            {isLoading ? "Loading..." : "Apply filters"}
          </button>
        </form>
        {error ? <p style={{ marginTop: "0.7rem", color: "var(--danger, #b42318)" }}>{error}</p> : null}
        {info ? <p style={{ marginTop: "0.7rem", color: "var(--ok, #067647)" }}>{info}</p> : null}
      </article>

      <section className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        {summaryCards.map((card) => (
          <article key={card.key} className="card" style={{ padding: "0.9rem" }}>
            <div style={{ color: "var(--ink-subtle)", fontSize: "0.84rem" }}>{card.label}</div>
            <div style={{ fontWeight: 800, fontSize: "1.3rem", marginTop: "0.25rem" }}>{card.value}</div>
            <div style={{ color: "var(--primary)", marginTop: "0.25rem", fontWeight: 600 }}>{card.sub}</div>
          </article>
        ))}
      </section>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Operational Actions</h2>

        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))" }}>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            Disable account user id
            <input value={disableUserId} onChange={(e) => setDisableUserId(e.target.value)} placeholder="user_123" />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            Disable reason
            <input value={disableReason} onChange={(e) => setDisableReason(e.target.value)} placeholder="reason" />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            Resend invite request id (optional)
            <input value={inviteRequestId} onChange={(e) => setInviteRequestId(e.target.value)} placeholder="link_req_123" />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            Incident id
            <input value={incidentId} onChange={(e) => setIncidentId(e.target.value)} placeholder="sos_123" />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            Incident decision
            <select value={incidentDecision} onChange={(e) => setIncidentDecision(e.target.value)}>
              <option value="approved">approved</option>
              <option value="needs_followup">needs_followup</option>
              <option value="rejected">rejected</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            Incident notes
            <input value={incidentNotes} onChange={(e) => setIncidentNotes(e.target.value)} placeholder="optional notes" />
          </label>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button
            type="button"
            className="button ghost"
            onClick={() => void runAction("disable-account")}
            disabled={busyAction === "disable-account"}
          >
            {busyAction === "disable-account" ? "Running..." : "Disable account"}
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={() => void runAction("resend-invite")}
            disabled={busyAction === "resend-invite"}
          >
            {busyAction === "resend-invite" ? "Running..." : "Resend invite"}
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={() => void runAction("incident-review")}
            disabled={busyAction === "incident-review"}
          >
            {busyAction === "incident-review" ? "Running..." : "Incident review"}
          </button>
          <button
            type="button"
            className="button"
            onClick={() => void exportReport("csv")}
            disabled={busyAction === "export-csv"}
          >
            {busyAction === "export-csv" ? "Exporting..." : "Export CSV"}
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={() => void exportReport("json")}
            disabled={busyAction === "export-json"}
          >
            {busyAction === "export-json" ? "Exporting..." : "Export JSON"}
          </button>
        </div>
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Feature Flags and Rollout</h2>
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {featureFlags.map((flag) => (
            <div
              key={flag.key}
              style={{
                display: "grid",
                gap: "0.15rem",
                padding: "0.65rem",
                border: "1px solid var(--line)",
                borderRadius: "0.5rem",
              }}
            >
              <strong>{flag.key}</strong>
              <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
                <label style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={flag.enabled}
                    onChange={(e) => updateLocalFlag(flag.key, { enabled: e.target.checked })}
                  />
                  Enabled
                </label>
                <label style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                  Rollout
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={flag.rollout_percentage}
                    onChange={(e) =>
                      updateLocalFlag(flag.key, {
                        rollout_percentage: Number.isNaN(Number(e.target.value)) ? 0 : Number(e.target.value),
                      })
                    }
                    style={{ width: "80px" }}
                  />
                  %
                </label>
              </div>
              <label style={{ display: "grid", gap: "0.3rem" }}>
                Roles (comma-separated)
                <input
                  value={flag.roles.join(",")}
                  onChange={(e) =>
                    updateLocalFlag(flag.key, {
                      roles: e.target.value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
              <label style={{ display: "grid", gap: "0.3rem" }}>
                Plans (comma-separated)
                <input
                  value={flag.plans.join(",")}
                  onChange={(e) =>
                    updateLocalFlag(flag.key, {
                      plans: e.target.value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
              <span style={{ color: "var(--ink-subtle)" }}>Updated: {new Date(flag.updated_at).toLocaleString()}</span>
              <button
                type="button"
                className="button"
                onClick={() => void updateFeatureFlag(flag)}
                disabled={updatingFlagKey === flag.key}
              >
                {updatingFlagKey === flag.key ? "Saving..." : "Save flag"}
              </button>
            </div>
          ))}
          {featureFlags.length === 0 ? (
            <p style={{ margin: 0, color: "var(--ink-subtle)" }}>No feature flags available.</p>
          ) : null}
        </div>
      </article>
    </section>
  );
}
