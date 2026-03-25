import { expect, test, type Page } from "@playwright/test";

const mockLogin = async (page: Page, role: "family_member" | "admin") => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: `mock-${role}-access-token`,
        refresh_token: `mock-${role}-refresh-token`,
        session_id: `mock-${role}-session-id`,
        role,
        permissions:
          role === "admin"
            ? ["admin:read", "admin:manage", "notification:read"]
            : ["health:read", "health:write", "notification:read"],
        user: {
          id: role === "admin" ? "u_admin" : "u_family",
          username: role === "admin" ? "admin@example.com" : "family@example.com",
          full_name: role === "admin" ? "Admin User" : "Family Member",
        },
      }),
    });
  });
};

test("family health-records workflow is accessible after sign-in", async ({ page }) => {
  await mockLogin(page, "family_member");

  await page.route("**/api/v1/health-records?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        data: {
          items: [
            {
              id: "hr-1",
              patient_id: "u_parent",
              record_type: "vitals",
              object_key: "docs/hr-1.pdf",
              created_at: "2026-03-20T10:00:00Z",
              data: { summary: "BP stable" },
            },
          ],
        },
        meta: { count: 1, total: 1, page: 1, page_size: 25 },
      }),
    });
  });

  await page.route("**/api/v1/health-records/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        data: { id: "hr-2" },
      }),
    });
  });

  await page.route("**/api/v1/health-records/*/document-download-url", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "success",
        data: {
          download_url: "https://example.com/document.pdf",
        },
      }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Email").fill("family@example.com");
  await page.getByLabel("Password").fill("Family@123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/family$/);
  await page.getByRole("link", { name: "Health Record Workspace" }).click();
  await expect(page.getByRole("heading", { name: "Health Records Workspace" })).toBeVisible();
  await expect(page.getByText("hr-1")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download" })).toBeEnabled();
});

test("admin dashboard core action workflow works", async ({ page }) => {
  await mockLogin(page, "admin");

  await page.route("**/api/v1/admin-analytics/dashboard?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        filters_applied: { geography: null, role: null, plan: null, time_window: "7d" },
        marketplace: { caregivers_total: 10, caregivers_approved: 8, bookings_total: 5 },
        subscriptions: { active_subscriptions: 7, conversion_events: 3, churn_events: 1 },
        sos: { incidents_total: 4, incidents_acknowledged: 3 },
        queue_health: { medication_pending: 2, notification_failures: 0, sos_open_incidents: 1 },
        alerts: [{ severity: "warning", message: "None" }],
        usage_cards: [],
      }),
    });
  });

  await page.route("**/api/v1/admin-analytics/feature-flags", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            key: "feature.x",
            enabled: true,
            rollout_percentage: 100,
            roles: ["admin"],
            plans: ["plus"],
            updated_at: "2026-03-24T08:00:00Z",
          },
        ],
      }),
    });
  });

  await page.route("**/api/v1/admin-analytics/actions/disable-account", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ action: "disable-account", detail: "Account disabled" }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@example.com");
  await page.getByLabel("Password").fill("Admin@123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "Admin Analytics and Operations" })).toBeVisible();

  await page.getByLabel("Disable account user id").fill("u_test");
  await page.getByRole("button", { name: "Disable account" }).click();
  await expect(page.getByText("disable-account: Account disabled")).toBeVisible();
});

test("notifications page consumes realtime websocket events", async ({ page }) => {
  await mockLogin(page, "family_member");

  await page.addInitScript(() => {
    class MockWebSocket {
      url: string;
      onmessage: ((event: { data: string }) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(url: string) {
        this.url = url;
        setTimeout(() => {
          this.onmessage?.({
            data: JSON.stringify({
              event_type: "notification.delivered",
              payload: { channel: "in_app", status: "delivered" },
            }),
          });
        }, 200);
      }

      close() {}
      send() {}
      addEventListener() {}
      removeEventListener() {}
    }

    // @ts-expect-error test runtime override
    window.WebSocket = MockWebSocket;
  });

  await page.route("**/api/v1/notifications/deliveries?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    });
  });

  await page.route("**/api/v1/notifications/preferences/**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "u_family",
          enabled_channels: ["in_app"],
          quiet_hours_start_utc: null,
          quiet_hours_end_utc: null,
          locale: "en-IN",
          accessibility_plain_text: false,
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user_id: "u_family",
        enabled_channels: ["in_app"],
        quiet_hours_start_utc: null,
        quiet_hours_end_utc: null,
        locale: "en-IN",
        accessibility_plain_text: false,
      }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Email").fill("family@example.com");
  await page.getByLabel("Password").fill("Family@123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.goto("/family/notifications");
  await expect(page.getByRole("heading", { name: "Notifications Center" })).toBeVisible();
  await expect(page.getByText("Realtime notification")).toBeVisible();
  await expect(page.getByText("in_app delivered")).toBeVisible();
});
