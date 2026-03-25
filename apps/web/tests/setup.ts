import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  if (typeof window !== "undefined") {
    window.localStorage.clear();
    document.cookie = "ec_role=; path=/; max-age=0";
    document.cookie = "ec_user=; path=/; max-age=0";
    document.cookie = "ec_uid=; path=/; max-age=0";
    document.cookie = "ec_username=; path=/; max-age=0";
    document.cookie = "ec_access=; path=/; max-age=0";
  }
});
