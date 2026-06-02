"use client";

import * as React from "react";
import {
  type CurrentUser,
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  setAccessToken,
  signup as apiSignup,
} from "@/lib/api";

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (tenantId: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<CurrentUser | null>(null);
  const [loading, setLoading] = React.useState(true);

  // On mount, try to restore a session via the httpOnly refresh cookie.
  React.useEffect(() => {
    let active = true;
    fetchCurrentUser()
      .then((u) => {
        if (active) setUser(u);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const login = React.useCallback(async (email: string, password: string) => {
    const r = await apiLogin(email, password);
    setUser({ user_id: r.user_id, tenant_id: r.tenant_id, email: r.email });
  }, []);

  const signup = React.useCallback(
    async (tenantId: string, email: string, password: string) => {
      const r = await apiSignup(tenantId, email, password);
      setUser({ user_id: r.user_id, tenant_id: r.tenant_id, email: r.email });
    },
    [],
  );

  const logout = React.useCallback(() => {
    apiLogout();
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = React.useMemo(
    () => ({ user, loading, login, signup, logout }),
    [user, loading, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = React.useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
