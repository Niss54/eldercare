"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button, Card } from "../../../components/ui";
import { ApiClientError, apiRequest, getApiErrorMessage } from "../../../lib/api-client";
import { AppRole, ROLE_HOME, ROLE_LABELS } from "../../../lib/roles";
import { useAuth } from "../../../providers/auth-provider";

export default function LoginPage() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("family@example.com");
  const [password, setPassword] = useState("Family@123");
  const [showPassword, setShowPassword] = useState(false);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [nextPath, setNextPath] = useState<string>(ROLE_HOME["family_member"]);

  useEffect(() => {
    const next = new URLSearchParams(window.location.search).get("next");
    if (next) {
      setNextPath(next);
    }
  }, []);

  const requestMfaChallenge = async (username: string): Promise<string> => {
    const challenge = await apiRequest<{ ticket: string }>("/api/v1/auth/mfa/challenge", {
      method: "POST",
      body: { username },
    });
    return challenge.ticket;
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const loginPayload: Record<string, string> = {
        email,
        password,
      };
      if (mfaTicket && mfaCode) {
        loginPayload.mfa_ticket = mfaTicket;
        loginPayload.mfa_code = mfaCode;
      }

      const payload = await apiRequest<{
        role: AppRole;
        user?: { id?: string; username?: string; full_name?: string };
        access_token: string;
        refresh_token: string;
        session_id: string;
        permissions?: string[];
      }>("/api/v1/auth/login", {
        method: "POST",
        body: loginPayload,
      });

      const role = payload.role as AppRole;
      signIn({
        role,
        displayName: payload.user?.full_name || payload.user?.username || "user",
        userId: payload.user?.id || "unknown",
        username: payload.user?.username || email,
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
        sessionId: payload.session_id,
        permissions: payload.permissions || [],
      });

      window.location.assign(nextPath || ROLE_HOME[role]);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401 && err.detail.toLowerCase().includes("mfa required") && !mfaTicket) {
        try {
          const ticket = await requestMfaChallenge(email);
          setMfaTicket(ticket);
          setError("MFA required for this role. Enter the one-time code and sign in again.");
          return;
        } catch (challengeErr) {
          setError(getApiErrorMessage(challengeErr, "Unable to request MFA challenge"));
          return;
        }
      }

      setError(getApiErrorMessage(err, "Login failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card as="section" style={{ border: "none", boxShadow: "none", background: "transparent" }}>
      <h1 style={{ marginTop: 0 }}>Secure Sign In</h1>
      <p style={{ color: "var(--ink-subtle)" }}>
        Use your backend account to create a JWT session and enter your protected role workspace.
      </p>
      <form onSubmit={submit} className="grid" style={{ gap: "0.8rem" }}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            style={{ width: "100%", marginTop: "0.35rem", padding: "0.6rem", borderRadius: 6, border: "1px solid var(--line)" }}
          />
        </label>
        <label>
          Password
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "0.5rem", marginTop: "0.35rem" }}>
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              style={{ width: "100%", padding: "0.6rem", borderRadius: 6, border: "1px solid var(--line)" }}
            />
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowPassword((current) => !current)}
              style={{ alignSelf: "stretch", borderRadius: 6, paddingInline: "0.7rem" }}
            >
              {showPassword ? "Hide" : "Show"}
            </Button>
          </div>
        </label>

        {mfaTicket ? (
          <label>
            MFA code
            <input
              value={mfaCode}
              onChange={(event) => setMfaCode(event.target.value)}
              placeholder="Enter OTP"
              style={{ width: "100%", marginTop: "0.35rem", padding: "0.6rem", borderRadius: 6, border: "1px solid var(--line)" }}
            />
          </label>
        ) : null}

        {error ? <p style={{ color: "var(--critical)", margin: 0 }}>{error}</p> : null}

        <Button type="submit" disabled={submitting} style={{ borderRadius: 6 }}>
          {submitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <p style={{ color: "var(--ink-subtle)", fontSize: "0.86rem", marginTop: "0.8rem" }}>
        Demo roles: {ROLE_LABELS.family_member} (family@example.com), {ROLE_LABELS.parent} (parent@example.com), {ROLE_LABELS.admin} (admin@example.com).
      </p>
    </Card>
  );
}
