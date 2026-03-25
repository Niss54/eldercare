"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "./ui";
import { AppRole, ROLE_LABELS } from "../lib/roles";
import { useAuth } from "../providers/auth-provider";

type NavItem = {
  href: string;
  label: string;
  roles: AppRole[];
};

const navItems: NavItem[] = [
  { href: "/family", label: "Family Hub", roles: ["family_member"] },
  { href: "/family/relationships", label: "Relationships", roles: ["family_member"] },
  { href: "/family/health-records", label: "Health Records", roles: ["family_member", "doctor"] },
  { href: "/family/consents", label: "Consents", roles: ["family_member", "parent"] },
  { href: "/family/notifications", label: "Notifications", roles: ["family_member", "caregiver", "parent"] },
  { href: "/family/medication", label: "Medication", roles: ["family_member", "caregiver", "doctor"] },
  { href: "/family/sos", label: "SOS", roles: ["family_member", "caregiver", "parent"] },
  { href: "/family/marketplace", label: "Marketplace", roles: ["family_member"] },
  { href: "/family/subscriptions", label: "Subscription", roles: ["family_member", "admin"] },
  { href: "/family/future", label: "Future Panels", roles: ["family_member", "admin"] },
  { href: "/admin", label: "Admin Ops", roles: ["admin"] },
];

export function PortalShell({ role, children }: { role: AppRole; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, signOut } = useAuth();

  const availableNav = navItems.filter((item) => item.roles.includes(role));

  const handleLogout = async () => {
    await signOut();
    router.push("/login");
  };

  return (
    <div>
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          backdropFilter: "blur(8px)",
          background: "rgba(246, 248, 245, 0.87)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div
          style={{
            width: "min(1200px, 100% - 2rem)",
            margin: "0 auto",
            display: "flex",
            gap: "0.8rem",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0.8rem 0",
          }}
        >
          <div>
            <div style={{ fontWeight: 800, letterSpacing: "0.03em" }}>ELDERCARE OPS</div>
            <div style={{ fontSize: "0.8rem", color: "var(--ink-subtle)" }}>
              {ROLE_LABELS[role]} portal {session ? `· ${session.displayName}` : ""}
            </div>
          </div>
          <Button variant="ghost" onClick={handleLogout} type="button">
            Log out
          </Button>
        </div>
      </header>
      <main>
        <nav className="card" style={{ padding: "0.6rem", marginBottom: "1rem" }}>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {availableNav.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="pill"
                  style={{
                    border: active ? "1px solid var(--primary)" : "1px solid var(--line)",
                    background: active ? "rgba(15, 118, 110, 0.1)" : "var(--surface)",
                    color: active ? "var(--primary-strong)" : "var(--ink-subtle)",
                    fontWeight: 600,
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>
        {children}
      </main>
    </div>
  );
}
