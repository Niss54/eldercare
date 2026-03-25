import { ApiClientError } from "../api-client";
import type { components } from "./schema";
import { createSdkClient } from "./client";

export type SosIncident = components["schemas"]["SosIncident"];
export type SosTimelineEvent = components["schemas"]["TimelineEvent"];

type TriggerPayload = components["schemas"]["TriggerSosRequest"];

const unwrapError = (error: unknown) => {
  if (error instanceof ApiClientError) {
    return error;
  }
  return new ApiClientError(500, "Request failed", error);
};

export const sosSdk = {
  async listIncidents(token: string): Promise<SosIncident[]> {
    try {
      const client = createSdkClient(token);
      const data = await client.get<{ count: number; items: SosIncident[] }>("/api/v1/sos/incidents", { cache: "no-store" });
      return Array.isArray(data.items) ? data.items : [];
    } catch (error) {
      throw unwrapError(error);
    }
  },

  async triggerIncident(token: string, payload: TriggerPayload): Promise<SosIncident> {
    try {
      const client = createSdkClient(token);
      const data = await client.post<SosIncident>("/api/v1/sos/incidents/trigger", payload);
      return data;
    } catch (error) {
      throw unwrapError(error);
    }
  },

  async getTimeline(token: string, incidentId: string): Promise<SosTimelineEvent[]> {
    try {
      const client = createSdkClient(token);
      const data = await client.get<{ count: number; items: SosTimelineEvent[] }>(
        `/api/v1/sos/incidents/${encodeURIComponent(incidentId)}/timeline`,
        {
        cache: "no-store",
        },
      );
      return Array.isArray(data.items) ? data.items : [];
    } catch (error) {
      throw unwrapError(error);
    }
  },
};
