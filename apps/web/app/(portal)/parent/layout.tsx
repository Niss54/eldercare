import { requireRole } from "../../../lib/auth";

export default function ParentLayout({ children }: { children: React.ReactNode }) {
  requireRole(["parent"]);
  return <>{children}</>;
}
