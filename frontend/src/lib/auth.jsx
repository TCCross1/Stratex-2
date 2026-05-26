import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { me as fetchMe } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined=checking, null=anon, obj=user
  const [token, setToken] = useState(() => localStorage.getItem("stratex_token"));

  const refresh = useCallback(async () => {
    if (!localStorage.getItem("stratex_token")) { setUser(null); return; }
    try { const u = await fetchMe(); setUser(u); } catch { setUser(null); localStorage.removeItem("stratex_token"); }
  }, []);

  useEffect(() => {
    // CRITICAL: Skip /me check during Google OAuth callback so the session can be exchanged first.
    if (typeof window !== "undefined" && window.location.hash && window.location.hash.includes("session_id=")) {
      setUser(null);
      return;
    }
    refresh();
  }, [refresh]);

  const login = (access_token, userObj) => {
    localStorage.setItem("stratex_token", access_token);
    setToken(access_token);
    setUser(userObj);
  };
  const logout = () => {
    localStorage.removeItem("stratex_token");
    setToken(null);
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, token, login, logout, refresh, setUser }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
