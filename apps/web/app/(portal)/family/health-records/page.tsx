"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { getApiErrorMessage } from "../../../../lib/api-client";
import { useApiClient } from "../../../../hooks/use-api-client";
import { useAuth } from "../../../../providers/auth-provider";

type HealthRecordItem = {
  id: string;
  subject_user_id?: string;
  patient_id?: string;
  data_type?: string;
  record_type?: string;
  object_key?: string | null;
  created_at?: string;
  updated_at?: string;
  data?: { summary?: string };
};

type ApiEnvelope<T> = {
  status?: string;
  message?: string;
  data?: T;
  meta?: {
    count?: number;
    total?: number;
    page?: number;
    page_size?: number;
  };
};

const RECORD_TYPES = ["medical_history", "lab_report", "prescription", "vitals"];

export default function FamilyHealthRecordsPage() {
  const { session } = useAuth();
  const apiClient = useApiClient();
  const [subjectUserId, setSubjectUserId] = useState("u_parent");
  const [recordType, setRecordType] = useState(RECORD_TYPES[0]);
  const [summary, setSummary] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [records, setRecords] = useState<HealthRecordItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [downloadingRecordId, setDownloadingRecordId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultLabel, setResultLabel] = useState("All records");

  useEffect(() => {
    if (!session?.accessToken) {
      return;
    }
    setSubjectUserId((previous) => previous || session.userId || "u_parent");
  }, [session]);

  const fetchRecords = useCallback(
    async (mode: "all" | "type" | "date") => {
      if (!apiClient.accessToken) {
        setError("Please sign in again to load health records.");
        return;
      }
      if (!subjectUserId.trim()) {
        setError("Subject user ID is required.");
        return;
      }

      const params = new URLSearchParams({ subject_user_id: subjectUserId.trim() });
      let endpoint = "/api/v1/health-records";

      if (mode === "type") {
        endpoint = "/api/v1/health-records/search/by-type";
        params.set("record_type", recordType);
      }

      if (mode === "date") {
        if (!dateFrom) {
          setError("Date filter ke liye date select karo.");
          return;
        }
        endpoint = "/api/v1/health-records/search/by-date-range";
        params.set("date_from", new Date(dateFrom).toISOString());
      }

      setIsLoading(true);
      setError(null);

      try {
        const payload = await apiClient.request<ApiEnvelope<{ items?: HealthRecordItem[] }> & { items?: HealthRecordItem[] }>(
          `${endpoint}?${params.toString()}`,
          {
          method: "GET",
          cache: "no-store",
          },
        );

        const envelopeItems = payload.data?.items;
        const legacyItems = payload.items;
        const items = Array.isArray(envelopeItems)
          ? (envelopeItems as HealthRecordItem[])
          : Array.isArray(legacyItems)
            ? (legacyItems as HealthRecordItem[])
            : [];
        setRecords(items);

        if (mode === "all") {
          setResultLabel("All records");
        } else if (mode === "type") {
          setResultLabel(`Filtered by type: ${recordType}`);
        } else {
          setResultLabel(`Filtered from: ${dateFrom}`);
        }
      } catch (err) {
        setError(getApiErrorMessage(err, "Network issue while loading health records."));
      } finally {
        setIsLoading(false);
      }
    },
    [apiClient, dateFrom, recordType, subjectUserId],
  );

  useEffect(() => {
    void fetchRecords("all");
  }, [fetchRecords]);

  const createRecord = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!apiClient.accessToken) {
      setError("Please sign in again to create records.");
      return;
    }
    if (!subjectUserId.trim()) {
      setError("Subject user ID is required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.request("/api/v1/health-records/", {
        method: "POST",
        body: {
          subject_user_id: subjectUserId.trim(),
          record_type: recordType,
          data: { summary: summary.trim() || "Created from family workspace" },
        },
      });

      setSummary("");
      await fetchRecords("all");
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while creating health record."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const downloadDocument = async (record: HealthRecordItem) => {
    if (!apiClient.accessToken) {
      setError("Please sign in again to download documents.");
      return;
    }

    setDownloadingRecordId(record.id);
    setError(null);

    try {
      const payload = await apiClient.request<ApiEnvelope<{ download_url: string }> & { download_url?: string }>(
        `/api/v1/health-records/${encodeURIComponent(record.id)}/document-download-url`,
        {
          method: "GET",
          cache: "no-store",
        },
      );
      const downloadUrl = payload.data?.download_url ?? payload.download_url;

      if (!downloadUrl) {
        setError("Download link unavailable for this record.");
        return;
      }

      window.open(downloadUrl, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(getApiErrorMessage(err, "Network issue while generating download link."));
    } finally {
      setDownloadingRecordId(null);
    }
  };

  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Health Records Workspace</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Live records from backend APIs with consent-aware access.</p>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <div className="card" style={{ padding: "0.8rem" }}>
            <div className="pill">Records</div>
            <h3>{records.length}</h3>
            <p>{resultLabel}</p>
          </div>
          <div className="card" style={{ padding: "0.8rem" }}>
            <div className="pill">State</div>
            <h3>{isLoading ? "Loading" : "Ready"}</h3>
            <p>{error ? "Needs attention" : "Connected"}</p>
          </div>
          <div className="card" style={{ padding: "0.8rem" }}>
            <div className="pill">Subject</div>
            <h3>{subjectUserId || "-"}</h3>
            <p>Consent-checked query scope</p>
          </div>
        </div>
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Create Record</h2>
        <form className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }} onSubmit={createRecord}>
          <label>
            Subject user ID
            <input
              value={subjectUserId}
              onChange={(e) => setSubjectUserId(e.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <label>
            Record type
            <select
              value={recordType}
              onChange={(e) => setRecordType(e.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", border: "1px solid var(--line)", borderRadius: 10 }}
            >
              {RECORD_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Summary
            <input
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Short clinical summary"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <button className="button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Create record"}
          </button>
        </form>
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Search</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", alignItems: "end" }}>
          <label>
            Filter from date
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <button className="button ghost" type="button" onClick={() => void fetchRecords("all")} disabled={isLoading}>
            All records
          </button>
          <button className="button ghost" type="button" onClick={() => void fetchRecords("type")} disabled={isLoading}>
            Search by type
          </button>
          <button className="button ghost" type="button" onClick={() => void fetchRecords("date")} disabled={isLoading}>
            Search by date
          </button>
        </div>
        {error ? (
          <p style={{ marginTop: "0.8rem", color: "var(--danger, #b42318)" }}>{error}</p>
        ) : null}
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Documents</h2>
        <div className="grid">
          {records.length === 0 ? <p style={{ color: "var(--ink-subtle)" }}>No records found for current filter.</p> : null}
          {records.map((record) => {
            const type = record.record_type ?? record.data_type ?? "unknown";
            const owner = record.patient_id ?? record.subject_user_id ?? "unknown";
            const date = record.created_at ? new Date(record.created_at).toLocaleDateString() : "-";
            const hasDocument = Boolean(record.object_key);

            return (
              <div key={record.id} className="card" style={{ padding: "0.7rem", display: "flex", justifyContent: "space-between" }}>
                <div>
                  <strong>{type}</strong>
                  <div style={{ color: "var(--ink-subtle)", fontSize: "0.85rem" }}>
                    {record.id} · {owner} · {date}
                  </div>
                  {record.data?.summary ? (
                    <div style={{ color: "var(--ink-subtle)", fontSize: "0.82rem", marginTop: "0.3rem" }}>{record.data.summary}</div>
                  ) : null}
                </div>
                <div style={{ display: "grid", alignItems: "start", gap: "0.35rem" }}>
                  <button
                    type="button"
                    className="button ghost"
                    onClick={() => void downloadDocument(record)}
                    disabled={!hasDocument || downloadingRecordId === record.id}
                    title={hasDocument ? "Download document" : "No document attached"}
                  >
                    {downloadingRecordId === record.id ? "Preparing..." : "Download"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </article>
    </section>
  );
}
