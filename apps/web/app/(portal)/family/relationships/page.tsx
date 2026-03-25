const relationships = [
  { parent: "Maya Sharma", status: "Linked", approvedAt: "2026-03-12" },
  { parent: "Rajesh Sharma", status: "Pending Approval", approvedAt: "-" },
];

export default function FamilyRelationshipsPage() {
  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Family-Parent Linking</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Invite, approve, and manage caregiver relationship lifecycles.</p>
        <form className="grid" style={{ gridTemplateColumns: "2fr 1fr auto", alignItems: "end" }}>
          <label>
            Parent email
            <input style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", border: "1px solid var(--line)", borderRadius: 10 }} placeholder="parent@example.com" />
          </label>
          <label>
            Relationship
            <select style={{ width: "100%", marginTop: "0.3rem", padding: "0.55rem", border: "1px solid var(--line)", borderRadius: 10 }}>
              <option>Primary family</option>
              <option>Secondary family</option>
              <option>Emergency contact</option>
            </select>
          </label>
          <button type="button" className="button">Send invite</button>
        </form>
      </article>

      <article className="card" style={{ padding: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Active Relationships</h2>
        <div className="grid">
          {relationships.map((row) => (
            <div key={row.parent} className="card" style={{ padding: "0.7rem", display: "flex", justifyContent: "space-between" }}>
              <div>
                <strong>{row.parent}</strong>
                <div style={{ color: "var(--ink-subtle)", fontSize: "0.9rem" }}>Approved: {row.approvedAt}</div>
              </div>
              <span className="pill">{row.status}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
