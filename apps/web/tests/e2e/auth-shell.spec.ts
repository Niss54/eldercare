import { expect, test } from "@playwright/test";

test("unauthenticated user is redirected to login for protected route", async ({ page }) => {
  await page.goto("/family");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Secure Sign In" })).toBeVisible();
});

test("login form submits with mocked backend and lands on role home", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "mock-access-token",
        refresh_token: "mock-refresh-token",
        session_id: "mock-session-id",
        role: "family_member",
        permissions: ["health:read"],
        user: {
          id: "u_family",
          username: "family@example.com",
          full_name: "Family Member",
        },
      }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Email").fill("family@example.com");
  await page.getByLabel("Password").fill("Family@123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/family$/, { timeout: 20000 });
  await expect(page.getByRole("heading", { name: "Family Operations Home" })).toBeVisible();
});
