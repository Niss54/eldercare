import { webEnv } from "../../../../lib/env";

const aiEnabled = webEnv.enableAiPanel;
const iotEnabled = webEnv.enableIotPanel;

export default function FamilyFuturePanelsPage() {
  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Future AI and IoT Panels</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Feature-flagged shells are available for staged rollout.</p>
      </article>
      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>AI Assistant Panel</h2>
        {aiEnabled ? <p>Enabled: risk summary and care recommendations surface here.</p> : <p style={{ color: "var(--ink-subtle)" }}>Disabled by flag `NEXT_PUBLIC_ENABLE_AI_PANEL`.</p>}
      </article>
      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>IoT Device Panel</h2>
        {iotEnabled ? <p>Enabled: device heartbeat and alert normalization appear here.</p> : <p style={{ color: "var(--ink-subtle)" }}>Disabled by flag `NEXT_PUBLIC_ENABLE_IOT_PANEL`.</p>}
      </article>
    </section>
  );
}
