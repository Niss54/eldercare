"use client";

import { useEffect, useState } from "react";

type Toast = {
  id: number;
  message: string;
  tone: "urgent" | "routine";
};

const realtimeFeed = [
  { message: "Medication reminder delivered to Maya's phone", tone: "routine" as const },
  { message: "Caregiver acknowledged wellness check", tone: "routine" as const },
  { message: "SOS drill event escalated to doctor backup", tone: "urgent" as const },
];

export function RealtimeToastDemo() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const id = window.setInterval(() => {
      const event = realtimeFeed[Math.floor(Math.random() * realtimeFeed.length)];
      const toast: Toast = { id: Date.now(), message: event.message, tone: event.tone };
      setToasts((previous) => [toast, ...previous].slice(0, 3));
    }, 6000);

    return () => window.clearInterval(id);
  }, []);

  return (
    <div style={{ position: "fixed", right: "1rem", bottom: "1rem", display: "grid", gap: "0.55rem", zIndex: 25 }}>
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="card"
          style={{
            padding: "0.7rem",
            width: "min(360px, calc(100vw - 2rem))",
            borderLeft: toast.tone === "urgent" ? "4px solid var(--critical)" : "4px solid var(--primary)",
            animation: "fadeIn 250ms ease-out",
          }}
        >
          <div style={{ fontSize: "0.78rem", color: "var(--ink-subtle)" }}>{toast.tone.toUpperCase()}</div>
          <div>{toast.message}</div>
        </div>
      ))}
    </div>
  );
}
