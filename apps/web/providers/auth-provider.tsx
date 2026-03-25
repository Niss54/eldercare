"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { apiRequest } from "../lib/api-client";
import { AppRole, ROLE_HOME } from "../lib/roles";
import { RoleSession } from "../types";

type AuthContextValue = {
  session: RoleSession | null;
  signIn: (payload: RoleSession) => void;
  signOut: () => Promise<void>;
  getDefaultHome: () => string;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const ACCESS_TOKEN_KEY = "ec_access_token";
const REFRESH_TOKEN_KEY = "ec_refresh_token";
const SESSION_ID_KEY = "ec_session_id";

const readCookie = (name: string): string | null => {
  if (typeof document === "undefined") {
    return null;
  }
  const pairs = document.cookie.split(";").map((item) => item.trim());
  const row = pairs.find((item) => item.startsWith(`${name}=`));
  return row ? decodeURIComponent(row.split("=")[1] ?? "") : null;
};

const writeCookie = (name: string, value: string, maxAgeSeconds = 60 * 60 * 8) => {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; samesite=lax`;
};

const readStorage = (key: string): string | null => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
};

const writeStorage = (key: string, value: string) => {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(key, value);
  }
};

const clearStorage = (key: string) => {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(key);
  }
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<RoleSession | null>(null);

  useEffect(() => {
    const role = readCookie("ec_role") as AppRole | null;
    const accessToken = readStorage(ACCESS_TOKEN_KEY);
    const refreshToken = readStorage(REFRESH_TOKEN_KEY);
    const sessionId = readStorage(SESSION_ID_KEY);

    if (!role || !accessToken || !refreshToken || !sessionId) {
      setSession(null);
      return;
    }

    setSession({
      role,
      displayName: readCookie("ec_user") ?? "user",
      userId: readCookie("ec_uid") ?? "unknown",
      username: readCookie("ec_username") ?? "unknown",
      accessToken,
      refreshToken,
      sessionId,
      permissions: [],
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      signIn: (payload) => {
        writeCookie("ec_role", payload.role);
        writeCookie("ec_user", payload.displayName);
        writeCookie("ec_uid", payload.userId);
        writeCookie("ec_username", payload.username);
        writeCookie("ec_access", payload.accessToken);
        writeStorage(ACCESS_TOKEN_KEY, payload.accessToken);
        writeStorage(REFRESH_TOKEN_KEY, payload.refreshToken);
        writeStorage(SESSION_ID_KEY, payload.sessionId);
        setSession(payload);
      },
      signOut: async () => {
        const active = session;
        if (active) {
          try {
            await apiRequest("/api/v1/auth/logout", {
              method: "POST",
              token: active.accessToken,
              body: {
                session_id: active.sessionId,
                refresh_token: active.refreshToken,
              },
            });
          } catch {
            // Local sign-out should still proceed even if backend is unavailable.
          }
        }

        writeCookie("ec_role", "", 0);
        writeCookie("ec_user", "", 0);
        writeCookie("ec_uid", "", 0);
        writeCookie("ec_username", "", 0);
        writeCookie("ec_access", "", 0);
        clearStorage(ACCESS_TOKEN_KEY);
        clearStorage(REFRESH_TOKEN_KEY);
        clearStorage(SESSION_ID_KEY);
        setSession(null);
      },
      getDefaultHome: () => {
        if (!session) {
          return "/login";
        }
        return ROLE_HOME[session.role];
      },
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
