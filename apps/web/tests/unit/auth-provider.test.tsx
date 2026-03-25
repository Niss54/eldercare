import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider, useAuth } from "../../providers/auth-provider";

function Harness() {
  const { session, signIn, signOut, getDefaultHome } = useAuth();

  return (
    <div>
      <button
        onClick={() =>
          signIn({
            role: "family_member",
            displayName: "Family Member",
            userId: "u_family",
            username: "family@example.com",
            accessToken: "access-token",
            refreshToken: "refresh-token",
            sessionId: "session-1",
            permissions: ["health:read"],
          })
        }
      >
        SignIn
      </button>
      <button onClick={() => void signOut()}>SignOut</button>
      <div data-testid="home">{getDefaultHome()}</div>
      <div data-testid="session">{session ? session.userId : "none"}</div>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ status: "success", data: {} }),
      })) as unknown as typeof fetch,
    );
  });

  it("stores session on sign-in and clears on sign-out", async () => {
    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText("SignIn"));

    expect(screen.getByTestId("session")).toHaveTextContent("u_family");
    expect(screen.getByTestId("home")).toHaveTextContent("/family");
    expect(window.localStorage.getItem("ec_access_token")).toBe("access-token");

    fireEvent.click(screen.getByText("SignOut"));

    await waitFor(() => {
      expect(screen.getByTestId("session")).toHaveTextContent("none");
      expect(window.localStorage.getItem("ec_access_token")).toBeNull();
    });
  });
});
