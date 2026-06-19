"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart2, LineChart, PieChart, Table, Hash, AlertCircle, Clock, Rows } from "lucide-react";
import type { HistoryEntry, ChartType } from "../../lib/types";
import { fetchHistory } from "../../lib/api";

const SESSION_KEY = "querymind_session_id";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(SESSION_KEY) ?? "";
}

const CHART_ICONS: Record<ChartType, React.ComponentType<{ className?: string }>> = {
  bar: BarChart2,
  line: LineChart,
  pie: PieChart,
  table: Table,
  number: Hash,
};

function formatTimestamp(ts: string): string {
  if (!ts) return "";
  try {
    return new Intl.DateTimeFormat("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(ts));
  } catch {
    return ts;
  }
}

interface EntryCardProps {
  entry: HistoryEntry;
  index: number;
}

function EntryCard({ entry, index }: EntryCardProps) {
  const ChartIcon = CHART_ICONS[entry.chart_type as ChartType] ?? Table;

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        entry.had_error
          ? "border-red-900/40 bg-red-950/10"
          : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 mt-0.5 text-xs font-mono text-zinc-600 w-6">
          #{index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-zinc-200 truncate">{entry.question}</p>
          {entry.insight && !entry.had_error && (
            <p className="mt-1 text-xs text-zinc-500 line-clamp-2">{entry.insight}</p>
          )}
          {entry.had_error && (
            <div className="mt-1 flex items-center gap-1 text-xs text-red-400">
              <AlertCircle className="w-3 h-3" />
              Query failed
            </div>
          )}
          <div className="mt-2 flex items-center gap-3 text-xs text-zinc-600">
            {!entry.had_error && (
              <span className="flex items-center gap-1">
                <ChartIcon className="w-3 h-3" />
                {entry.chart_type}
              </span>
            )}
            {entry.row_count > 0 && (
              <span className="flex items-center gap-1">
                <Rows className="w-3 h-3" />
                {entry.row_count.toLocaleString()} rows
              </span>
            )}
            {entry.execution_time_ms > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {entry.execution_time_ms}ms
              </span>
            )}
            {entry.timestamp && (
              <span className="ml-auto">{formatTimestamp(entry.timestamp)}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState("");

  useEffect(() => {
    const id = getSessionId();
    setSessionId(id);
    if (!id) {
      setLoading(false);
      return;
    }
    fetchHistory(id)
      .then((data) => setEntries(data.entries))
      .catch(() => setError("Failed to load history"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-10 flex items-center gap-4 border-b border-zinc-800 bg-zinc-950 px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-sm font-semibold text-zinc-200">Query History</h1>
        <span className="ml-auto text-xs text-zinc-600 font-mono truncate max-w-[200px]">
          {sessionId ? `Session: ${sessionId.slice(0, 8)}…` : "No session"}
        </span>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded-xl bg-zinc-900 animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-900/40 bg-red-950/20 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && entries.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <Clock className="w-8 h-8 text-zinc-700" />
            <p className="text-sm text-zinc-500">No queries yet in this session.</p>
            <Link
              href="/"
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              Ask your first question →
            </Link>
          </div>
        )}

        {!loading && !error && entries.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-zinc-600 mb-4">
              {entries.length} {entries.length === 1 ? "query" : "queries"} this session
            </p>
            {entries.map((entry, i) => (
              <EntryCard key={i} entry={entry} index={i} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
