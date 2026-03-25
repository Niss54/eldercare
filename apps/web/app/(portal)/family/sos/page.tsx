import { SosTimeline } from "../../../../components/sos-timeline";

export default function FamilySosPage() {
  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Emergency SOS</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Immediate trigger control with a live escalation timeline.</p>
      </article>
      <SosTimeline />
    </section>
  );
}
