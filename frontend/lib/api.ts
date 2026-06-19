import type {
  QueryResponse,
  SchemaResponse,
  HistoryResponse,
  SuggestedQuestionsResponse,
  HealthResponse,
  DbConnection,
} from "./types";
import { getToken, authHeaders } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail ?? message;
    } catch {}
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function submitQuery(
  question: string,
  sessionId: string,
  connectionId?: string | null
): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      session_id: sessionId,
      connection_id: connectionId ?? null,
    }),
  });
}

export async function fetchSchema(connectionId?: string | null): Promise<SchemaResponse> {
  const params = connectionId ? `?connection_id=${connectionId}` : "";
  return apiFetch<SchemaResponse>(`/schema${params}`);
}

export async function fetchHistory(sessionId: string): Promise<HistoryResponse> {
  return apiFetch<HistoryResponse>(`/history/${sessionId}`);
}

export async function deleteHistory(sessionId: string): Promise<void> {
  await apiFetch(`/history/${sessionId}`, { method: "DELETE" });
}

export async function fetchSuggestedQuestions(): Promise<SuggestedQuestionsResponse> {
  return apiFetch<SuggestedQuestionsResponse>("/suggested-questions");
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// ── DB Connection management ──────────────────────────────────────────────────
export async function fetchConnections(): Promise<DbConnection[]> {
  return apiFetch<DbConnection[]>("/connections");
}

export async function createConnection(
  name: string,
  connectionString: string,
  dbType = "postgresql"
): Promise<DbConnection> {
  return apiFetch<DbConnection>("/connections", {
    method: "POST",
    body: JSON.stringify({ name, connection_string: connectionString, db_type: dbType }),
  });
}

export async function deleteConnection(id: string): Promise<void> {
  await apiFetch(`/connections/${id}`, { method: "DELETE" });
}

export async function testConnection(id: string): Promise<{ status: string; message: string }> {
  return apiFetch(`/connections/${id}/test`, { method: "POST" });
}
