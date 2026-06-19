"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";

interface SQLViewerProps {
  sql: string;
}

export function SQLViewer({ sql }: SQLViewerProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!sql) return null;

  return (
    <div className="rounded-xl border border-zinc-800 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors"
      >
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />
        )}
        <span className="font-mono text-blue-400">SQL</span>
        <span className="ml-1 text-zinc-600">— click to {open ? "collapse" : "expand"}</span>
      </button>

      {open && (
        <div className="relative border-t border-zinc-800 bg-zinc-900">
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-green-400" />
                <span className="text-green-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copy
              </>
            )}
          </button>
          <pre className="overflow-x-auto p-4 pr-20 text-xs text-zinc-300 font-mono leading-relaxed">
            <code>{sql}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
