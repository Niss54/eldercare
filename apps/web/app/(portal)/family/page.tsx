import Link from "next/link";

const quickLinks = [
  ["Relationship Onboarding", "/family/relationships"],
  ["Health Record Workspace", "/family/health-records"],
  ["Consent Ledger", "/family/consents"],
  ["Notification Center", "/family/notifications"],
  ["Medication Calendar", "/family/medication"],
  ["SOS Incident Timeline", "/family/sos"],
  ["Caregiver Marketplace", "/family/marketplace"],
  ["Subscriptions & Entitlements", "/family/subscriptions"],
  ["Future AI + IoT Panels", "/family/future"],
] as const;

export default function FamilyPortalPage() {
  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Family Operations Home</h1>
        <p style={{ color: "var(--ink-subtle)" }}>
          End-to-end family workflows for linked caregiving, consented data access, emergency action, and growth flows.
        </p>
      </article>
      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Feature Workspaces</h2>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
          {quickLinks.map(([label, href]) => (
            <Link key={href} href={href} className="card" style={{ padding: "0.8rem", borderStyle: "dashed" }}>
              <strong>{label}</strong>
            </Link>
          ))}
        </div>
      </article>
    </section>
  );
}
