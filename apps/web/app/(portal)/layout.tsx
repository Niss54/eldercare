import { PortalShell } from "../../components/portal-shell";
import { requireSignedInRole } from "../../lib/auth";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const role = requireSignedInRole();
  return <PortalShell role={role}>{children}</PortalShell>;
}
