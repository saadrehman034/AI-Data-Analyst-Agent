"use client";

import { Bot, User } from "lucide-react";
import type { Message } from "../lib/types";
import { InsightCard } from "./InsightCard";
import { ChartRenderer } from "./ChartRenderer";
import { SQLViewer } from "./SQLViewer";

interface MessageBubbleProps {
  message: Message;
}

function SkeletonLoader() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 bg-zinc-800 rounded w-3/4" />
      <div className="h-4 bg-zinc-800 rounded w-1/2" />
      <div className="h-32 bg-zinc-800 rounded-xl w-full mt-4" />
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-3">
        <div className="max-w-[70%] rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-3 text-sm text-white shadow-sm">
          {message.content}
        </div>
        <div className="flex-shrink-0 mt-1 flex h-7 w-7 items-center justify-center rounded-full bg-zinc-700">
          <User className="h-4 w-4 text-zinc-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 mt-1 flex h-7 w-7 items-center justify-center rounded-full bg-blue-900/60 border border-blue-700/50">
        <Bot className="h-4 w-4 text-blue-400" />
      </div>
      <div className="flex-1 min-w-0 space-y-3">
        {message.loading ? (
          <div className="rounded-2xl rounded-tl-sm border border-zinc-800 bg-zinc-900 p-4">
            <SkeletonLoader />
          </div>
        ) : message.response ? (
          <>
            {message.response.error ? (
              <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-400">
                {message.response.insight ||
                  "I couldn't answer that question. Try rephrasing it or check the schema explorer to see what data is available."}
              </div>
            ) : (
              <>
                <InsightCard
                  insight={message.response.insight}
                  executionTimeMs={message.response.execution_time_ms}
                  rowCount={message.response.row_count}
                />
                {message.response.results.length > 0 && (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                    <ChartRenderer
                      chartType={message.response.chart_type}
                      chartConfig={message.response.chart_config}
                      data={message.response.results}
                      columns={message.response.columns}
                    />
                  </div>
                )}
                <SQLViewer sql={message.response.sql} />
              </>
            )}
          </>
        ) : (
          <div className="rounded-2xl rounded-tl-sm border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm text-zinc-300">
            {message.content}
          </div>
        )}
      </div>
    </div>
  );
}
