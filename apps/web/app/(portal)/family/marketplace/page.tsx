"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { webEnv } from "../../../../lib/env";
import { useAuth } from "../../../../providers/auth-provider";

type Caregiver = {
  id: string;
  full_name: string;
  skills: string[];
  languages: string[];
  location: string;
  availability: string;
  bio?: string | null;
  rating: number;
  verification_status: string;
};

export default function FamilyMarketplacePage() {
  const { session } = useAuth();
  const [caregivers, setCaregivers] = useState<Caregiver[]>([]);
  const [query, setQuery] = useState("");
  const [skill, setSkill] = useState("");
  const [language, setLanguage] = useState("");
  const [availability, setAvailability] = useState("");
  const [location, setLocation] = useState("");
  const [bookingStartAt, setBookingStartAt] = useState("");
  const [bookingNotes, setBookingNotes] = useState("");
  const [bookingBusyId, setBookingBusyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [canBook, setCanBook] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const authHeaders = useMemo(() => {
    if (!session?.accessToken) {
      return null;
    }
    return {
      Authorization: `Bearer ${session.accessToken}`,
      "Content-Type": "application/json",
    };
  }, [session]);

  const loadEntitlement = useCallback(async () => {
    if (!authHeaders) {
      return;
    }
    try {
      const response = await fetch(
        `${webEnv.apiBaseUrl}/api/v1/subscriptions/entitlements/check?feature=${encodeURIComponent("marketplace.booking")}`,
        { headers: authHeaders, cache: "no-store" },
      );
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      setCanBook(Boolean(payload.enabled));
    } catch {
      // Keep booking UI available; backend still enforces entitlement.
    }
  }, [authHeaders]);

  const loadCaregivers = useCallback(async () => {
    if (!authHeaders) {
      setError("Please sign in again to access marketplace.");
      return;
    }
    const params = new URLSearchParams();
    if (query.trim()) params.set("query", query.trim());
    if (skill.trim()) params.set("skill", skill.trim());
    if (language.trim()) params.set("language", language.trim());
    if (availability.trim()) params.set("availability", availability.trim());
    if (location.trim()) params.set("location", location.trim());

    setIsLoading(true);
    setError(null);
    setInfo(null);
    try {
      const response = await fetch(`${webEnv.apiBaseUrl}/api/v1/marketplace/caregivers?${params.toString()}`, {
        method: "GET",
        headers: authHeaders,
        cache: "no-store",
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(typeof payload?.detail === "string" ? payload.detail : "Unable to load caregivers.");
        return;
      }
      setCaregivers(Array.isArray(payload.items) ? (payload.items as Caregiver[]) : []);
    } catch {
      setError("Network issue while loading caregivers.");
    } finally {
      setIsLoading(false);
    }
  }, [authHeaders, availability, language, location, query, skill]);

  useEffect(() => {
    void loadEntitlement();
    void loadCaregivers();
  }, [loadCaregivers, loadEntitlement]);

  const onBook = async (caregiverId: string) => {
    if (!authHeaders) {
      setError("Please sign in again to create booking.");
      return;
    }
    if (!bookingStartAt) {
      setError("Booking start date/time select karo.");
      return;
    }

    setBookingBusyId(caregiverId);
    setError(null);
    setInfo(null);

    try {
      const response = await fetch(`${webEnv.apiBaseUrl}/api/v1/marketplace/bookings`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          caregiver_id: caregiverId,
          start_time: new Date(bookingStartAt).toISOString(),
          notes: bookingNotes.trim() || null,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(typeof payload?.detail === "string" ? payload.detail : "Unable to create booking.");
        return;
      }
      setInfo(`Booking requested: ${payload.id}`);
      setBookingNotes("");
    } catch {
      setError("Network issue while creating booking.");
    } finally {
      setBookingBusyId(null);
    }
  };

  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Caregiver Marketplace</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Search, filter, and book verified caregivers from backend services.</p>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          <label>
            Search
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="name or keyword"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <label>
            Skill filter
            <input
              value={skill}
              onChange={(e) => setSkill(e.target.value)}
              placeholder="e.g. medication"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <label>
            Language
            <input
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="e.g. en"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <label>
            Availability
            <input
              value={availability}
              onChange={(e) => setAvailability(e.target.value)}
              placeholder="e.g. weekday"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <label>
            Location
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Bangalore"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <button type="button" className="button" onClick={() => void loadCaregivers()} disabled={isLoading}>
            {isLoading ? "Searching..." : "Apply filters"}
          </button>
        </div>

        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", marginTop: "0.8rem" }}>
          <label>
            Booking start
            <input
              type="datetime-local"
              value={bookingStartAt}
              onChange={(e) => setBookingStartAt(e.target.value)}
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
          <label>
            Notes
            <input
              value={bookingNotes}
              onChange={(e) => setBookingNotes(e.target.value)}
              placeholder="optional note"
              style={{ width: "100%", marginTop: "0.3rem", padding: "0.5rem", border: "1px solid var(--line)", borderRadius: 10 }}
            />
          </label>
        </div>

        {error ? <p style={{ color: "var(--danger, #b42318)", marginTop: "0.8rem" }}>{error}</p> : null}
        {info ? <p style={{ color: "var(--ok, #067647)", marginTop: "0.8rem" }}>{info}</p> : null}
      </article>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        {caregivers.map((caregiver) => (
          <article className="card" key={caregiver.id} style={{ padding: "0.9rem" }}>
            <h2 style={{ marginTop: 0 }}>{caregiver.full_name}</h2>
            <p style={{ color: "var(--ink-subtle)", minHeight: "2.2rem" }}>{caregiver.bio || caregiver.skills.join(", ")}</p>
            <p style={{ margin: "0.35rem 0" }}><strong>Skills:</strong> {caregiver.skills.join(", ") || "-"}</p>
            <p style={{ margin: "0.35rem 0" }}><strong>Languages:</strong> {caregiver.languages.join(", ") || "-"}</p>
            <p style={{ margin: "0.35rem 0" }}><strong>Location:</strong> {caregiver.location}</p>
            <p style={{ margin: "0.35rem 0" }}><strong>Availability:</strong> {caregiver.availability}</p>
            <p style={{ margin: "0.35rem 0", fontWeight: 700 }}>Rating: {caregiver.rating.toFixed(1)} / 5</p>
            <p style={{ margin: "0.35rem 0", color: "var(--ink-subtle)" }}>Verification: {caregiver.verification_status}</p>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <button
                type="button"
                className="button"
                disabled={!canBook || bookingBusyId === caregiver.id}
                title={canBook ? "" : "Upgrade plan to book"}
                onClick={() => void onBook(caregiver.id)}
              >
                {bookingBusyId === caregiver.id ? "Booking..." : canBook ? "Book" : "Upgrade to book"}
              </button>
            </div>
          </article>
        ))}
      </div>

      {caregivers.length === 0 && !isLoading ? (
        <article className="card" style={{ padding: "0.9rem" }}>
          <p style={{ margin: 0, color: "var(--ink-subtle)" }}>No caregivers found for current filters.</p>
        </article>
      ) : null}
    </section>
  );
}
