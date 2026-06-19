export type ChartType = "bar" | "line" | "pie" | "number" | "table";

export interface ChartConfig {
  chart_type: ChartType;
  x_axis: string | null;
  y_axis: string | null;
  title: string;
}

export interface QueryResponse {
  session_id: string;
  question: string;
  sql: string;
  results: Record<string, unknown>[];
  columns: string[];
  chart_type: ChartType;
  chart_config: ChartConfig;
  insight: string;
  execution_time_ms: number;
  row_count: number;
  error: string | null;
}

export interface SchemaColumn {
  name: string;
  type: string;
}

export interface SchemaTable {
  name: string;
  row_count: number;
  columns: SchemaColumn[];
}

export interface SchemaResponse {
  tables: SchemaTable[];
}

export interface HistoryEntry {
  question: string;
  sql: string;
  insight: string;
  chart_type: ChartType;
  row_count: number;
  execution_time_ms: number;
  had_error: boolean;
  timestamp: string;
}

export interface HistoryResponse {
  session_id: string;
  entries: HistoryEntry[];
}

export interface SuggestedQuestionsResponse {
  questions: string[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  db: string;
  analyst_db: string;
  llm: string;
}

export interface UserOut {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserOut;
}

export interface DbConnection {
  id: string;
  name: string;
  db_type: string;
  is_demo: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
  timestamp: Date;
  loading?: boolean;
}
