"use client";

import { Lightbulb } from "lucide-react";

interface InsightCardProps {
  insight: string;
  executionTimeMs: number;
  rowCount: number;
}

export function InsightCard({ insight, executionTimeMs, rowCount }: InsightCardProps) {
  return (
    <div className="rounded-xl border border-blue-900/40 bg-blue-950/30 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex-shrink-0 rounded-lg bg-blue-600/20 p-1.5">
          <Lightbulb className="w-4 h-4 text-blue-400" />
        </div>
        <p className="text-sm text-zinc-100 leading-relaxed">{insight}</p>
      </div>
      <div className="mt-3 flex items-center gap-3 text-xs text-zinc-500">
        <span className="rounded-full bg-zinc-800 px-2 py-0.5">
          {rowCount.toLocaleString()} {rowCount === 1 ? "row" : "rows"}
        </span>
        <span className="rounded-full bg-zinc-800 px-2 py-0.5">
          {executionTimeMs}ms
        </span>
      </div>
    </div>
  );
}
