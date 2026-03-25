import { ApiClientError } from "../api-client";
import type { components } from "./schema";
import { createSdkClient } from "./client";

export type NotificationDelivery = components["schemas"]["Delivery"];
export type NotificationPreference = components["schemas"]["UserNotificationPreference"];

type PutPreference = components["schemas"]["PutPreferenceRequest"];

type SendPayload = components["schemas"]["SendNotificationRequest"];

const unwrapError = (error: unknown) => {
  if (error instanceof ApiClientError) {
    return error;
  }
  return new ApiClientError(500, "Request failed", error);
};

export const notificationsSdk = {
  async listDeliveries(token: string, recipientUserId?: string): Promise<NotificationDelivery[]> {
    try {
      const client = createSdkClient(token);
      const data = await client.get<{ count: number; items: NotificationDelivery[] }>("/api/v1/notifications/deliveries", {
        query: { recipient_user_id: recipientUserId },
        cache: "no-store",
      });
      return Array.isArray(data.items) ? data.items : [];
    } catch (error) {
      throw unwrapError(error);
    }
  },

  async getPreference(token: string, userId: string): Promise<NotificationPreference> {
    try {
      const client = createSdkClient(token);
      const data = await client.get<NotificationPreference>(`/api/v1/notifications/preferences/${encodeURIComponent(userId)}`, {
        cache: "no-store",
      });
      return data;
    } catch (error) {
      throw unwrapError(error);
    }
  },

  async putPreference(token: string, userId: string, payload: PutPreference): Promise<NotificationPreference> {
    try {
      const client = createSdkClient(token);
      const data = await client.put<NotificationPreference>(
        `/api/v1/notifications/preferences/${encodeURIComponent(userId)}`,
        payload,
      );
      return data;
    } catch (error) {
      throw unwrapError(error);
    }
  },

  async sendNotification(token: string, payload: SendPayload): Promise<NotificationDelivery[]> {
    try {
      const client = createSdkClient(token);
      const data = await client.post<{ count: number; items: NotificationDelivery[] }>("/api/v1/notifications/send", payload);
      return Array.isArray(data.items) ? data.items : [];
    } catch (error) {
      throw unwrapError(error);
    }
  },
};
