import type { UserOut, TokenResponse } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "qm_access_token";
const USER_KEY = "qm_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): UserOut | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as UserOut) : null;
  } catch {
    return null;
  }
}

export function storeSession(token: string, user: UserOut): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function authPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail ?? `HTTP ${res.status}`);
  return json as T;
}

export async function apiRegister(
  email: string,
  password: string,
  fullName?: string
): Promise<TokenResponse> {
  const data = await authPost<TokenResponse>("/auth/register", {
    email,
    password,
    full_name: fullName ?? null,
  });
  storeSession(data.access_token, data.user);
  return data;
}

export async function apiLogin(email: string, password: string): Promise<TokenResponse> {
  const data = await authPost<TokenResponse>("/auth/login", { email, password });
  storeSession(data.access_token, data.user);
  return data;
}

export async function apiLogout(): Promise<void> {
  await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(),
  }).catch(() => {});
  clearSession();
}

export async function fetchMe(): Promise<UserOut | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: "include",
    });
    if (!res.ok) {
      clearSession();
      return null;
    }
    return res.json() as Promise<UserOut>;
  } catch {
    return null;
  }
}
