import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import FamilyPortalPage from "../../app/(portal)/family/page";

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("Family portal home", () => {
  it("renders family workspace links", () => {
    render(<FamilyPortalPage />);

    expect(screen.getByRole("heading", { name: "Family Operations Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Health Record Workspace" })).toHaveAttribute("href", "/family/health-records");
    expect(screen.getByRole("link", { name: "Consent Ledger" })).toHaveAttribute("href", "/family/consents");
    expect(screen.getByRole("link", { name: "Subscriptions & Entitlements" })).toHaveAttribute("href", "/family/subscriptions");
  });
});
