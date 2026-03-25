/* eslint-disable */
// Generated from OpenAPI schema (apps/web/openapi/openapi.json).
// Regenerate with: npm run sdk:generate

export interface components {
  schemas: {
    Delivery: {
      id: string;
      channel: string;
      priority: string;
      status: string;
      message: string;
      created_at: string;
      provider_name: string;
    };
    UserNotificationPreference: {
      user_id: string;
      enabled_channels: string[];
      quiet_hours_start_utc?: number | null;
      quiet_hours_end_utc?: number | null;
      locale: string;
      accessibility_plain_text: boolean;
    };
    TimelineEvent: {
      id: string;
      timestamp: string;
      event_type: string;
      detail: string;
      metadata?: Record<string, string>;
    };
    SosIncident: {
      id: string;
      subject_user_id: string;
      initiated_by_user_id: string;
      status: string;
      severity: string;
      created_at: string;
      acknowledged_by?: string | null;
      acknowledged_at?: string | null;
      resolved_by?: string | null;
      resolved_at?: string | null;
      timeline?: components["schemas"]["TimelineEvent"][];
    };
    PutPreferenceRequest: {
      enabled_channels: string[];
      quiet_hours_start_utc?: number | null;
      quiet_hours_end_utc?: number | null;
      locale: string;
      accessibility_plain_text: boolean;
    };
    SendNotificationRequest: {
      recipient_user_id: string;
      message: string;
      channels: string[];
      priority?: string;
      dedup_key?: string | null;
      mode?: string;
    };
    TriggerSosRequest: {
      subject_user_id: string;
      severity?: string;
      cascade?: Array<Record<string, unknown>>;
    };
  };
}

export interface paths {
  "/api/v1/notifications/deliveries": {
    get: {
      parameters: {
        query?: {
          recipient_user_id?: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              count: number;
              items: components["schemas"]["Delivery"][];
            };
          };
        };
      };
    };
  };
  "/api/v1/notifications/preferences/{user_id}": {
    get: {
      parameters: {
        path: { user_id: string };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["UserNotificationPreference"];
          };
        };
      };
    };
    put: {
      parameters: {
        path: { user_id: string };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["PutPreferenceRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["UserNotificationPreference"];
          };
        };
      };
    };
  };
  "/api/v1/notifications/send": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["SendNotificationRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              count: number;
              items: components["schemas"]["Delivery"][];
            };
          };
        };
      };
    };
  };
  "/api/v1/sos/incidents": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              count: number;
              items: components["schemas"]["SosIncident"][];
            };
          };
        };
      };
    };
  };
  "/api/v1/sos/incidents/trigger": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["TriggerSosRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["SosIncident"];
          };
        };
      };
    };
  };
  "/api/v1/sos/incidents/{incident_id}/timeline": {
    get: {
      parameters: {
        path: { incident_id: string };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              count: number;
              items: components["schemas"]["TimelineEvent"][];
            };
          };
        };
      };
    };
  };
  "/api/v1/realtime/events/{channel}": {
    get: {
      parameters: {
        path: { channel: string };
        query?: { limit?: number; topic?: string };
      };
      responses: {
        200: {
          content: {
            "application/json": {
              count: number;
              items: Array<{
                id: string;
                channel: string;
                event_type: string;
                topic?: string | null;
                payload: Record<string, unknown>;
                timestamp: string;
              }>;
            };
          };
        };
      };
    };
  };
}
