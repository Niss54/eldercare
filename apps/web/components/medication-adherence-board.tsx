"use client";

import { useMemo, useState } from "react";

type Slot = {
  id: string;
  day: string;
  time: string;
  medication: string;
};

const schedule: Slot[] = [
  { id: "mon-am", day: "Mon", time: "08:00", medication: "Lisinopril 10mg" },
  { id: "mon-pm", day: "Mon", time: "20:00", medication: "Metformin 500mg" },
  { id: "tue-am", day: "Tue", time: "08:00", medication: "Lisinopril 10mg" },
  { id: "tue-pm", day: "Tue", time: "20:00", medication: "Metformin 500mg" },
  { id: "wed-am", day: "Wed", time: "08:00", medication: "Lisinopril 10mg" },
  { id: "wed-pm", day: "Wed", time: "20:00", medication: "Metformin 500mg" },
];

export function MedicationAdherenceBoard() {
  const [taken, setTaken] = useState<Record<string, boolean>>({});

  const adherence = useMemo(() => {
    const total = schedule.length;
    const completed = schedule.filter((slot) => taken[slot.id]).length;
    return total === 0 ? 0 : Math.round((completed / total) * 100);
  }, [taken]);

  return (
    <section className="card" style={{ padding: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", marginBottom: "0.8rem" }}>
        <h2 style={{ margin: 0 }}>Medication Calendar</h2>
        <span className="pill">Adherence {adherence}%</span>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}>
        {schedule.map((slot) => {
          const checked = Boolean(taken[slot.id]);
          return (
            <label
              key={slot.id}
              className="card"
              style={{
                padding: "0.75rem",
                borderColor: checked ? "var(--primary)" : "var(--line)",
                background: checked ? "rgba(15, 118, 110, 0.08)" : "var(--surface)",
              }}
            >
              <div style={{ fontWeight: 700 }}>{slot.day}</div>
              <div style={{ color: "var(--ink-subtle)", fontSize: "0.9rem" }}>{slot.time}</div>
              <div style={{ margin: "0.4rem 0" }}>{slot.medication}</div>
              <input
                checked={checked}
                onChange={(event) => {
                  setTaken((previous) => ({ ...previous, [slot.id]: event.target.checked }));
                }}
                type="checkbox"
              />{" "}
              Taken
            </label>
          );
        })}
      </div>
    </section>
  );
}
