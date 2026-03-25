"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "../lib/api-client";
import { webEnv } from "../lib/env";
import { sosSdk, type SosIncident, type SosTimelineEvent } from "../lib/sdk/sos";
import { useAuth } from "../providers/auth-provider";

type IncidentEvent = {
  id: string;
  at: string;
  text: string;
  eventType: string;
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

const formatEvent = (item: SosTimelineEvent): IncidentEvent => ({
  id: item.id,
  at: new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  text: item.detail,
  eventType: item.event_type,
});

const mergeEvents = (incoming: IncidentEvent[], existing: IncidentEvent[]) => {
  const byId = new Map<string, IncidentEvent>();
  for (const event of existing) {
    byId.set(event.id, event);
  }
  for (const event of incoming) {
    byId.set(event.id, event);
  }
  return Array.from(byId.values()).sort((a, b) => a.id.localeCompare(b.id));
};

export function SosTimeline() {
  const { session } = useAuth();
  const [incidents, setIncidents] = useState<SosIncident[]>([]);
  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<IncidentEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const incidentOpen = useMemo(() => incidents.some((incident) => incident.status !== "resolved"), [incidents]);

  const loadIncidents = useCallback(async () => {
    if (!session?.accessToken) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const items = await sosSdk.listIncidents(session.accessToken);
      setIncidents(items);
      const newest = items[items.length - 1] ?? null;
      setActiveIncidentId((previous) => previous ?? newest?.id ?? null);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load SOS incidents."));
    } finally {
      setIsLoading(false);
    }
  }, [session?.accessToken]);

  const loadTimeline = useCallback(async () => {
    if (!session?.accessToken || !activeIncidentId) {
      setTimeline([]);
      return;
    }
    try {
      const items = await sosSdk.getTimeline(session.accessToken, activeIncidentId);
      setTimeline(items.map(formatEvent));
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load SOS timeline."));
    }
  }, [activeIncidentId, session?.accessToken]);

  useEffect(() => {
    void loadIncidents();
  }, [loadIncidents]);

  useEffect(() => {
    void loadTimeline();
  }, [loadTimeline]);

  useEffect(() => {
    if (!session?.accessToken) {
      return;
    }
    const wsBase = toWsUrl(webEnv.apiBaseUrl);
    const ws = new WebSocket(`${wsBase}/ws/sos?token=${encodeURIComponent(session.accessToken)}`);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          event_type?: string;
          topic?: string;
          payload?: { incident_id?: string; severity?: string; subject_user_id?: string };
        };

        if (payload.event_type === "ws.connected" || payload.event_type === "ws.pong") {
          return;
        }

        const incidentId = payload.payload?.incident_id;
        if (incidentId && (!activeIncidentId || activeIncidentId === incidentId)) {
          const optimistic: IncidentEvent = {
            id: `ws-${Date.now()}`,
            at: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            text: `${payload.event_type ?? "sos.update"} received from realtime channel`,
            eventType: payload.event_type ?? "sos.update",
          };
          setTimeline((previous) => mergeEvents([optimistic], previous));
        }

        void loadIncidents();
        if (incidentId && activeIncidentId === incidentId) {
          void loadTimeline();
        }
      } catch {
        // Ignore malformed payloads from websocket.
      }
    };

    return () => {
      ws.close();
    };
  }, [activeIncidentId, loadIncidents, loadTimeline, session?.accessToken]);

  const triggerIncident = async () => {
    if (!session?.accessToken || !session.userId) {
      return;
    }
    setIsTriggering(true);
    setError(null);

    const optimisticEvent: IncidentEvent = {
      id: `tmp-${Date.now()}`,
      at: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      text: "Emergency signal sent through SOS cascade (pending confirmation)",
      eventType: "incident.triggering",
    };
    setTimeline((previous) => mergeEvents([optimisticEvent], previous));

    try {
      const incident = await sosSdk.triggerIncident(session.accessToken, {
        subject_user_id: session.userId,
        severity: "critical",
      });
      setIncidents((previous) => [...previous.filter((item) => item.id !== incident.id), incident]);
      setActiveIncidentId(incident.id);
      await loadTimeline();
    } catch (err) {
      setTimeline((previous) => previous.filter((item) => item.id !== optimisticEvent.id));
      setError(getApiErrorMessage(err, "Unable to trigger SOS incident."));
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <section className="card" style={{ padding: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.7rem", marginBottom: "0.8rem" }}>
        <h2 style={{ margin: 0 }}>Incident Timeline</h2>
        <button
          type="button"
          className="button"
          onClick={() => void triggerIncident()}
          style={{ background: "var(--critical)" }}
          disabled={isTriggering}
          aria-busy={isTriggering}
        >
          {isTriggering ? "Triggering..." : "Trigger SOS"}
        </button>
      </div>
      <p style={{ color: "var(--ink-subtle)", marginTop: 0 }}>
        Status: {incidentOpen ? "Live - escalations in progress" : "Standby"}
      </p>
      <p style={{ color: "var(--ink-subtle)", marginTop: 0 }}>
        {isLoading ? "Loading incidents..." : activeIncidentId ? `Tracking incident ${activeIncidentId}` : "No active incident yet."}
      </p>
      {error ? (
        <p role="status" aria-live="polite" style={{ color: "var(--danger, #b42318)" }}>
          {error}
        </p>
      ) : null}
      <div className="grid" role="list" aria-label="SOS incident timeline">
        {timeline.map((item) => (
          <div key={item.id} className="card" role="listitem" style={{ padding: "0.65rem 0.8rem" }}>
            <div style={{ fontSize: "0.78rem", color: "var(--ink-subtle)" }}>{item.at}</div>
            <div>{item.text}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
