"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { History, LayoutDashboard, Database, LogOut, ChevronDown, User } from "lucide-react";
import Link from "next/link";

import type { Message, DbConnection } from "../lib/types";
import { submitQuery, fetchConnections } from "../lib/api";
import { ChatInput } from "../components/ChatInput";
import { MessageBubble } from "../components/MessageBubble";
import { SchemaExplorer } from "../components/SchemaExplorer";
import { SuggestedQuestions } from "../components/SuggestedQuestions";
import { useAuth } from "../components/AuthProvider";

const SESSION_KEY = "querymind_session_id";
const CONN_KEY = "querymind_connection_id";

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return uuidv4();
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = uuidv4();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export default function HomePage() {
  const { user, loading: authLoading, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState<string>(getOrCreateSessionId);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [connections, setConnections] = useState<DbConnection[]>([]);
  const [activeConnectionId, setActiveConnectionId] = useState<string | null>(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!user) return;
    fetchConnections().then((list) => {
      setConnections(list);
      const savedId = sessionStorage.getItem(CONN_KEY);
      const match = savedId ? list.find((c) => c.id === savedId) : null;
      setActiveConnectionId(match ? match.id : (list[0]?.id ?? null));
    });
  }, [user]);

  const activeConn = connections.find((c) => c.id === activeConnectionId);

  const handleSubmit = useCallback(
    async (question: string) => {
      if (loading) return;

      const userMsg: Message = { id: uuidv4(), role: "user", content: question, timestamp: new Date() };
      const loadingMsg: Message = { id: uuidv4(), role: "assistant", content: "", timestamp: new Date(), loading: true };

      setMessages((prev) => [...prev, userMsg, loadingMsg]);
      setLoading(true);

      try {
        const result = await submitQuery(question, sessionId, activeConnectionId);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id ? { ...m, loading: false, content: result.insight, response: result } : m
          )
        );
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : "Request failed";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? {
                  ...m,
                  loading: false,
                  content: errMsg,
                  response: {
                    session_id: sessionId, question, sql: "", results: [], columns: [],
                    chart_type: "table",
                    chart_config: { chart_type: "table", x_axis: null, y_axis: null, title: "" },
                    insight: "I couldn't connect to the server. Please check that the backend is running.",
                    execution_time_ms: 0, row_count: 0, error: errMsg,
                  },
                }
              : m
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [loading, sessionId, activeConnectionId]
  );

  function handleTableClick(tableName: string) {
    setPendingQuestion(`Show me all columns and a sample of data from ${tableName}`);
  }

  useEffect(() => {
    if (pendingQuestion) {
      handleSubmit(pendingQuestion);
      setPendingQuestion(null);
    }
  }, [pendingQuestion, handleSubmit]);

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950">
        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-64 flex-shrink-0 flex flex-col border-r border-zinc-800">
          <div className="flex items-center gap-2 px-3 py-4 border-b border-zinc-800">
            <LayoutDashboard className="w-4 h-4 text-blue-500" />
            <span className="font-semibold text-sm text-zinc-200">QueryMind</span>
            <Link
              href="/history"
              className="ml-auto p-1.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors"
              title="Query history"
            >
              <History className="w-4 h-4" />
            </Link>
          </div>

          {/* Connection selector */}
          {connections.length > 0 && (
            <div className="px-3 py-2 border-b border-zinc-800">
              <p className="text-xs text-zinc-600 mb-1.5">Active database</p>
              <select
                value={activeConnectionId ?? ""}
                onChange={(e) => {
                  setActiveConnectionId(e.target.value || null);
                  sessionStorage.setItem(CONN_KEY, e.target.value);
                }}
                className="w-full bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500"
              >
                {connections.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex-1 overflow-hidden">
            <SchemaExplorer onTableClick={handleTableClick} connectionId={activeConnectionId} />
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0">
        <header className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="p-1.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors"
            aria-label="Toggle schema sidebar"
          >
            <LayoutDashboard className="w-4 h-4" />
          </button>
          <span className="text-sm font-medium text-zinc-400">
            {messages.length > 0
              ? `${Math.ceil(messages.length / 2)} question${Math.ceil(messages.length / 2) !== 1 ? "s" : ""} this session`
              : "New session"}
          </span>
          {activeConn && (
            <span className="hidden sm:flex items-center gap-1 text-xs text-zinc-600 border border-zinc-800 rounded px-2 py-0.5">
              <Database className="w-3 h-3" />
              {activeConn.name}
            </span>
          )}

          <div className="ml-auto flex items-center gap-2">
            <Link
              href="/connections"
              className="flex items-center gap-1.5 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              Databases
            </Link>
            <Link
              href="/history"
              className="flex items-center gap-1.5 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-colors"
            >
              <History className="w-3.5 h-3.5" />
              History
            </Link>

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu((s) => !s)}
                className="flex items-center gap-1.5 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-colors"
              >
                <User className="w-3.5 h-3.5" />
                {user?.full_name?.split(" ")[0] ?? user?.email?.split("@")[0] ?? "Account"}
                <ChevronDown className="w-3 h-3" />
              </button>
              {showUserMenu && (
                <div className="absolute right-0 top-full mt-1.5 w-48 bg-zinc-900 border border-zinc-800 rounded-xl shadow-xl z-50 overflow-hidden">
                  <div className="px-3 py-2.5 border-b border-zinc-800">
                    <p className="text-xs font-medium text-zinc-300 truncate">{user?.email}</p>
                  </div>
                  <Link
                    href="/connections"
                    className="flex items-center gap-2 px-3 py-2.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Database className="w-3.5 h-3.5" />
                    Manage databases
                  </Link>
                  <button
                    onClick={() => { setShowUserMenu(false); logout(); }}
                    className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-red-400 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <SuggestedQuestions onSelect={handleSubmit} />
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        <ChatInput onSubmit={handleSubmit} loading={loading} />
      </div>
    </div>
  );
}
