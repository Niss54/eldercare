import { MedicationAdherenceBoard } from "../../../../components/medication-adherence-board";

export default function FamilyMedicationPage() {
  return (
    <section className="grid">
      <article className="card" style={{ padding: "1rem" }}>
        <h1 style={{ marginTop: 0 }}>Medication Schedule</h1>
        <p style={{ color: "var(--ink-subtle)" }}>Calendar and adherence state with quick update controls.</p>
      </article>
      <MedicationAdherenceBoard />
    </section>
  );
}
