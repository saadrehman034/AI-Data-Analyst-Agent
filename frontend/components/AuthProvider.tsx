"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import type { UserOut } from "../lib/types";
import { fetchMe, apiLogout, getStoredUser } from "../lib/auth";

interface AuthContext {
  user: UserOut | null;
  loading: boolean;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthContext>({
  user: null,
  loading: true,
  logout: async () => {},
  refresh: async () => {},
});

const PUBLIC_PATHS = ["/login", "/register"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const refresh = useCallback(async (): Promise<void> => {
    const me = await fetchMe();
    setUser(me);
  }, []);

  useEffect(() => {
    // Hydrate from localStorage first (instant), then verify with server
    const cached = getStoredUser();
    if (cached) setUser(cached);

    refresh().finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    if (loading) return;
    const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
    if (!user && !isPublic) {
      router.replace("/login");
    }
  }, [user, loading, pathname, router]);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <Ctx.Provider value={{ user, loading, logout, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  return useContext(Ctx);
}
