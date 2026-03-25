import { requireRole } from "../../../lib/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  requireRole(["admin"]);
  return <>{children}</>;
}
