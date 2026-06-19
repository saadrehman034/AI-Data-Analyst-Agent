"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { fetchSuggestedQuestions } from "../lib/api";

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  const [questions, setQuestions] = useState<string[]>([]);

  useEffect(() => {
    fetchSuggestedQuestions()
      .then((data) => setQuestions(data.questions))
      .catch(() => {});
  }, []);

  if (questions.length === 0) return null;

  return (
    <div className="flex flex-col items-center gap-6 py-12 px-4">
      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-900/40 border border-blue-800/50">
          <Sparkles className="w-6 h-6 text-blue-400" />
        </div>
        <h2 className="text-lg font-semibold text-zinc-200">QueryMind</h2>
        <p className="text-sm text-zinc-500 text-center max-w-xs">
          Ask any question about your business data in plain English
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            className="text-left rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-xs text-zinc-400 hover:border-blue-700/60 hover:bg-zinc-800 hover:text-zinc-200 transition-all duration-150"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
