export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <div className="card" style={{ width: "min(640px, 100%)", padding: "1.3rem" }}>
        {children}
      </div>
    </main>
  );
}
