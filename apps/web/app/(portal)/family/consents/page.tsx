"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "../../../../lib/api-client";
import { useApiClient } from "../../../../hooks/use-api-client";
import { useAuth } from "../../../../providers/auth-provider";

type ConsentGrant = {
  id: string;
  subject_user_id: string;
  accessor_user_id: string;
  scopes: string[];
  status: "requested" | "granted" | "revoked" | "expired";
  created_at?: string;
  expires_at?: string | null;
};

type ConsentEvidence = {
  id: string;
  grant_id?: string | null;
  event_type: string;
  actor_user_id: string;
  reason?: string | null;
  timestamp: string;
};

export default function FamilyConsentsPage() {
  const { session } = useAuth();
  const apiClient = useApiClient();

  const [scopes, setScopes] = useState<string[]>([]);
  const [grants, setGrants] = useState<ConsentGrant[]>([]);
  const [evidence, setEvidence] = useState<ConsentEvidence[]>([]);

  const [accessorUserId, setAccessorUserId] = useState("u_caregiver_1");
  const [selectedScope, setSelectedScope] = useState("");
  const [expiresInDays, setExpiresInDays] = useState(30);
  const [revokeReason, setRevokeReason] = useState("User revoked access");
  const [grantStatusFilter, setGrantStatusFilter] = useState<"all" | ConsentGrant["status"]>("all");
  const [evidenceTypeFilter, setEvidenceTypeFilter] = useState("");
  const [evidenceSinceDate, setEvidenceSinceDate] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [isGranting, setIsGranting] = useState(false);
  const [revokingGrantId, setRevokingGrantId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const canMutate = Boolean(apiClient.accessToken);

  const loadData = useCallback(async () => {
    if (!apiClient.accessToken) {
      setError("Please sign in again to manage consent.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [scopePayload, grantsPayload, evidencePayload] = await Promise.all([
        apiClient.request<{ items?: string[] }>("/api/v1/consent/scopes", { method: "GET", cache: "no-store" }),
        apiClient.request<{ items?: ConsentGrant[] }>("/api/v1/consent/grants/mine", { method: "GET", cache: "no-store" }),
        apiClient.request<{ items?: ConsentEvidence[] }>(
          `/api/v1/consent/evidence?${new URLSearchParams(
            Object.fromEntries(
              Object.entries({
                event_type: evidenceTypeFilter.trim() || undefined,
                since: evidenceSinceDate ? new Date(evidenceSinceDate).toISOString() : undefined,
              }).filter(([, value]) => typeof value === "string" && value.length > 0),
            ),
          ).toString()}`,
          { method: "GET", cache: "no-store" },
        ),
      ]);

      const loadedScopes = Array.isArray(scopePayload.items) ? scopePayload.items : [];
      setScopes(loadedScopes);
      setSelectedScope((previous) => previous || loadedScopes[0] || "");
      setGrants(Array.isArray(grantsPayload.items) ? grantsPayload.items : []);
      setEvidence(Array.isArray(evidencePayload.items) ? evidencePayload.items : []);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to load consent data."));
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, evidenceSinceDate, evidenceTypeFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const grantedCount = useMemo(() => grants.filter((item) => item.status === "granted").length, [grants]);
  const visibleGrants = useMemo(
    () => (grantStatusFilter === "all" ? grants : grants.filter((item) => item.status === grantStatusFilter)),
    [grantStatusFilter, grants],
  );
  const visibleEvidence = useMemo(
    () =>
      evidence.filter((entry) => {
        if (evidenceTypeFilter.trim() && !entry.event_type.toLowerCase().includes(evidenceTypeFilter.trim().toLowerCase())) {
          return false;
        }
        if (evidenceSinceDate) {
          const threshold = new Date(evidenceSinceDate).getTime();
          if (Number.isFinite(threshold) && new Date(entry.timestamp).getTime() < threshold) {
            return false;
          }
        }
        return true;
      }),
    [evidence, evidenceSinceDate, evidenceTypeFilter],
  );

  const createGrant = async () => {
    if (!canMutate || !selectedScope) {
      setError("Select a scope and sign in again.");
      return;
    }
    if (!accessorUserId.trim()) {
      setError("Accessor user ID is required.");
      return;
    }

    setIsGranting(true);
    setError(null);
    setInfo(null);

    try {
      await apiClient.request("/api/v1/consent/grants", {
        method: "POST",
        body: {
          accessor_user_id: accessorUserId.trim(),
          scopes: [selectedScope],
          subject_user_id: session?.userId,
          expires_in_days: expiresInDays,
        },
      });
      setInfo("Consent granted.");
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to grant consent."));
    } finally {
      setIsGranting(false);
    }
  };

  const revokeGrant = async (grantId: string) => {
    if (!canMutate) {
      setError("Please sign in again to revoke consent.");
      return;
    }

    setRevokingGrantId(grantId);
    setError(null);
    setInfo(null);

    try {
      await apiClient.request(`/api/v1/consent/grant/${encodeURIComponent(grantId)}/revoke`, {
        method: "POST",
        body: { reason: revokeReason.trim() || "Revoked by subject" },
      });
      setInfo("Consent revoked.");
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to revoke consent."));
    } finally {
      setRevokingGrantId(null);
    }
  };

  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Consent Management</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Grant and revoke consent scopes with audit evidence visibility.</p>

        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <div className="card" style={{ padding: "0.8rem" }}>
            <div className="pill">Grants</div>
            <h3>{grants.length}</h3>
            <p>Total consent grants</p>
          </div>
          <div className="card" style={{ padding: "0.8rem" }}>
            <div className="pill">Active</div>
            <h3>{grantedCount}</h3>
            <p>Currently granted</p>
          </div>
          <div className="card" style={{ padding: "0.8rem" }}>
            <div className="pill">Evidence</div>
            <h3>{evidence.length}</h3>
            <p>Audit events</p>
          </div>
        </div>

        <div className="grid" style={{ marginTop: "0.8rem", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", alignItems: "end" }}>
          <label>
            Accessor user ID
            <input
              value={accessorUserId}
              onChange={(event) => setAccessorUserId(event.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", borderRadius: 10, border: "1px solid var(--line)" }}
            />
          </label>

          <label>
            Scope
            <select
              value={selectedScope}
              onChange={(event) => setSelectedScope(event.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", borderRadius: 10, border: "1px solid var(--line)" }}
            >
              {scopes.map((scope) => (
                <option key={scope} value={scope}>
                  {scope}
                </option>
              ))}
              {scopes.length === 0 ? <option value="">No scopes available</option> : null}
            </select>
          </label>

          <label>
            Expires in days
            <input
              type="number"
              min={1}
              max={365}
              value={expiresInDays}
              onChange={(event) => setExpiresInDays(Number(event.target.value) || 30)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", borderRadius: 10, border: "1px solid var(--line)" }}
            />
          </label>

          <button type="button" className="button" onClick={() => void createGrant()} disabled={isGranting || !canMutate || isLoading}>
            {isGranting ? "Granting..." : "Grant access"}
          </button>
        </div>

        <label style={{ display: "block", marginTop: "0.8rem" }}>
          Revoke reason
          <input
            value={revokeReason}
            onChange={(event) => setRevokeReason(event.target.value)}
            style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", borderRadius: 10, border: "1px solid var(--line)" }}
          />
        </label>

        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.7rem", flexWrap: "wrap" }}>
          <button type="button" className="button ghost" onClick={() => void loadData()} disabled={isLoading}>
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {error ? <p style={{ marginTop: "0.7rem", color: "var(--danger, #b42318)" }}>{error}</p> : null}
        {info ? <p style={{ marginTop: "0.7rem", color: "var(--ok, #067647)" }}>{info}</p> : null}
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Scope History</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", marginBottom: "0.7rem" }}>
          <label>
            Grant status filter
            <select
              value={grantStatusFilter}
              onChange={(event) => setGrantStatusFilter(event.target.value as "all" | ConsentGrant["status"])}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", borderRadius: 10, border: "1px solid var(--line)" }}
            >
              <option value="all">All</option>
              <option value="requested">Requested</option>
              <option value="granted">Granted</option>
              <option value="revoked">Revoked</option>
              <option value="expired">Expired</option>
            </select>
          </label>
        </div>

        {isLoading ? <p style={{ color: "var(--ink-subtle)" }}>Loading consent history...</p> : null}
        {!isLoading && visibleGrants.length === 0 ? <p style={{ color: "var(--ink-subtle)" }}>No consent grants found for current filter.</p> : null}

        <div className="grid">
          {visibleGrants.map((row) => (
            <div key={row.id} className="card" style={{ padding: "0.7rem", display: "flex", justifyContent: "space-between", gap: "0.8rem" }}>
              <div>
                <strong>{row.scopes.join(", ")}</strong>
                <div style={{ color: "var(--ink-subtle)", fontSize: "0.85rem" }}>
                  {row.id} · accessor: {row.accessor_user_id}
                </div>
                <div style={{ color: "var(--ink-subtle)", fontSize: "0.85rem" }}>
                  {row.expires_at ? `Expires ${new Date(row.expires_at).toLocaleDateString()}` : "No expiry"}
                </div>
              </div>

              <div style={{ display: "grid", gap: "0.4rem", justifyItems: "end" }}>
                <span className="pill">{row.status}</span>
                {row.status === "granted" ? (
                  <button
                    type="button"
                    className="button ghost"
                    onClick={() => void revokeGrant(row.id)}
                    disabled={revokingGrantId === row.id}
                  >
                    {revokingGrantId === row.id ? "Revoking..." : "Revoke"}
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Consent Evidence</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", marginBottom: "0.7rem" }}>
          <label>
            Event type filter
            <input
              value={evidenceTypeFilter}
              onChange={(event) => setEvidenceTypeFilter(event.target.value)}
              placeholder="consent.granted"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", borderRadius: 10, border: "1px solid var(--line)" }}
            />
          </label>
          <label>
            Since
            <input
              type="datetime-local"
              value={evidenceSinceDate}
              onChange={(event) => setEvidenceSinceDate(event.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", borderRadius: 10, border: "1px solid var(--line)" }}
            />
          </label>
          <button type="button" className="button ghost" onClick={() => void loadData()} disabled={isLoading}>
            Apply evidence filters
          </button>
        </div>
        {isLoading ? <p style={{ color: "var(--ink-subtle)" }}>Loading evidence timeline...</p> : null}
        {!isLoading && visibleEvidence.length === 0 ? <p style={{ color: "var(--ink-subtle)" }}>No evidence records for current filter.</p> : null}

        <div className="grid">
          {visibleEvidence.slice(0, 12).map((entry) => (
            <div key={entry.id} className="card" style={{ padding: "0.7rem" }}>
              <strong>{entry.event_type}</strong>
              <div style={{ color: "var(--ink-subtle)", fontSize: "0.85rem" }}>
                {entry.id} · actor: {entry.actor_user_id}
              </div>
              <div style={{ color: "var(--ink-subtle)", fontSize: "0.85rem" }}>
                {new Date(entry.timestamp).toLocaleString()}
              </div>
              {entry.reason ? <div style={{ marginTop: "0.25rem" }}>{entry.reason}</div> : null}
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
