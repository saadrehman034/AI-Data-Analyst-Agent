"use client";

import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Database, Table2, RefreshCw } from "lucide-react";
import type { SchemaTable } from "../lib/types";
import { fetchSchema } from "../lib/api";

const TYPE_COLORS: Record<string, string> = {
  integer: "text-amber-400",
  bigint: "text-amber-400",
  smallint: "text-amber-400",
  numeric: "text-green-400",
  real: "text-green-400",
  double: "text-green-400",
  decimal: "text-green-400",
  text: "text-blue-400",
  varchar: "text-blue-400",
  "character varying": "text-blue-400",
  boolean: "text-purple-400",
  date: "text-pink-400",
  timestamp: "text-pink-400",
  "timestamp with time zone": "text-pink-400",
  uuid: "text-zinc-500",
};

function typeColor(dataType: string): string {
  const lower = dataType.toLowerCase();
  for (const [key, color] of Object.entries(TYPE_COLORS)) {
    if (lower.includes(key)) return color;
  }
  return "text-zinc-500";
}

function shortType(dataType: string): string {
  const lower = dataType.toLowerCase();
  if (lower.includes("character varying") || lower.includes("varchar")) return "varchar";
  if (lower.includes("timestamp with time zone")) return "timestamptz";
  if (lower.includes("timestamp")) return "timestamp";
  if (lower.includes("double precision")) return "float";
  return lower;
}

interface TableRowProps {
  table: SchemaTable;
  onTableClick: (name: string) => void;
}

function TableRow({ table, onTableClick }: TableRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-zinc-800/50 last:border-0">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-zinc-800/50 transition-colors group"
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
        )}
        <Table2 className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
        <span
          className="flex-1 text-xs font-mono font-medium text-zinc-200 group-hover:text-blue-300 transition-colors cursor-pointer truncate"
          onClick={(e) => {
            e.stopPropagation();
            onTableClick(table.name);
          }}
        >
          {table.name}
        </span>
        <span className="text-xs text-zinc-600 tabular-nums flex-shrink-0">
          {table.row_count.toLocaleString()}
        </span>
      </button>

      {expanded && (
        <div className="pb-2 pl-8">
          {table.columns.map((col) => (
            <div key={col.name} className="flex items-center gap-2 py-0.5 px-2">
              <span className="text-xs font-mono text-zinc-400 truncate flex-1">{col.name}</span>
              <span className={`text-xs font-mono flex-shrink-0 ${typeColor(col.type)}`}>
                {shortType(col.type)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface SchemaExplorerProps {
  onTableClick: (tableName: string) => void;
  connectionId?: string | null;
}

export function SchemaExplorer({ onTableClick, connectionId }: SchemaExplorerProps) {
  const [tables, setTables] = useState<SchemaTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSchema(connectionId);
      setTables(data.tables);
    } catch (e) {
      setError("Failed to load schema");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [connectionId]);

  return (
    <aside className="flex flex-col h-full border-r border-zinc-800 bg-zinc-950">
      <div className="flex items-center justify-between px-3 py-3 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-500" />
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Schema</span>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-1 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-40"
          aria-label="Refresh schema"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="space-y-1 p-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-8 rounded bg-zinc-800/60 animate-pulse" />
            ))}
          </div>
        )}
        {error && (
          <div className="p-3 text-xs text-red-400">{error}</div>
        )}
        {!loading && !error && tables.map((table) => (
          <TableRow
            key={table.name}
            table={table}
            onTableClick={onTableClick}
          />
        ))}
      </div>

      {!loading && !error && (
        <div className="border-t border-zinc-800 px-3 py-2">
          <p className="text-xs text-zinc-600">
            {tables.length} tables · {tables.reduce((s, t) => s + t.row_count, 0).toLocaleString()} rows total
          </p>
        </div>
      )}
    </aside>
  );
}
