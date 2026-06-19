"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Database, RefreshCw, Search } from "lucide-react";
import type { SchemaTable } from "../../lib/types";
import { fetchSchema } from "../../lib/api";

const TYPE_BADGE_COLORS: Record<string, string> = {
  int: "bg-amber-900/30 text-amber-400 border-amber-800/50",
  numeric: "bg-green-900/30 text-green-400 border-green-800/50",
  decimal: "bg-green-900/30 text-green-400 border-green-800/50",
  real: "bg-green-900/30 text-green-400 border-green-800/50",
  double: "bg-green-900/30 text-green-400 border-green-800/50",
  float: "bg-green-900/30 text-green-400 border-green-800/50",
  text: "bg-blue-900/30 text-blue-400 border-blue-800/50",
  varchar: "bg-blue-900/30 text-blue-400 border-blue-800/50",
  char: "bg-blue-900/30 text-blue-400 border-blue-800/50",
  bool: "bg-purple-900/30 text-purple-400 border-purple-800/50",
  date: "bg-pink-900/30 text-pink-400 border-pink-800/50",
  time: "bg-pink-900/30 text-pink-400 border-pink-800/50",
  uuid: "bg-zinc-800 text-zinc-500 border-zinc-700",
};

function typeBadgeClass(dataType: string): string {
  const lower = dataType.toLowerCase();
  for (const [key, cls] of Object.entries(TYPE_BADGE_COLORS)) {
    if (lower.includes(key)) return cls;
  }
  return "bg-zinc-800 text-zinc-500 border-zinc-700";
}

function shortType(dataType: string): string {
  const lower = dataType.toLowerCase();
  if (lower.includes("character varying")) return "varchar";
  if (lower.includes("timestamp with time zone")) return "timestamptz";
  if (lower.includes("timestamp")) return "timestamp";
  if (lower.includes("double precision")) return "float8";
  return lower;
}

function TableCard({ table }: { table: SchemaTable }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-mono font-semibold text-zinc-200">{table.name}</span>
        </div>
        <span className="text-xs text-zinc-500 tabular-nums">
          {table.row_count.toLocaleString()} rows
        </span>
      </div>
      <div className="divide-y divide-zinc-800/50">
        {table.columns.map((col) => (
          <div key={col.name} className="flex items-center gap-3 px-4 py-2.5">
            <span className="flex-1 text-xs font-mono text-zinc-300">{col.name}</span>
            <span
              className={`flex-shrink-0 rounded-md border px-2 py-0.5 text-xs font-mono ${typeBadgeClass(col.type)}`}
            >
              {shortType(col.type)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SchemaPage() {
  const [tables, setTables] = useState<SchemaTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSchema();
      setTables(data.tables);
    } catch {
      setError("Failed to load schema. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = tables.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.columns.some((c) => c.name.toLowerCase().includes(search.toLowerCase()))
  );

  const totalRows = tables.reduce((s, t) => s + t.row_count, 0);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-10 flex items-center gap-4 border-b border-zinc-800 bg-zinc-950 px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-sm font-semibold text-zinc-200">Database Schema</h1>
        <div className="flex-1 max-w-xs">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tables and columns…"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-900 pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 focus:border-blue-600 focus:outline-none transition-colors"
            />
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {!loading && !error && (
          <div className="mb-6 flex items-center gap-4 text-xs text-zinc-500">
            <span>{tables.length} tables</span>
            <span>·</span>
            <span>{totalRows.toLocaleString()} total rows</span>
            <span>·</span>
            <span>{tables.reduce((s, t) => s + t.columns.length, 0)} columns</span>
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-48 rounded-xl bg-zinc-900 animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-900/40 bg-red-950/20 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map((table) => (
              <TableCard key={table.name} table={table} />
            ))}
            {filtered.length === 0 && (
              <p className="col-span-full text-sm text-zinc-500 text-center py-8">
                No tables match "{search}"
              </p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
