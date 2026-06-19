"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Database, Plus, Trash2, CheckCircle, XCircle, ArrowLeft, Loader2 } from "lucide-react";
import type { DbConnection } from "../../lib/types";
import { fetchConnections, createConnection, deleteConnection, testConnection } from "../../lib/api";
import { useAuth } from "../../components/AuthProvider";

export default function ConnectionsPage() {
  const { user } = useAuth();
  const [connections, setConnections] = useState<DbConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", connection_string: "" });
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { status: string; message: string }>>({});

  useEffect(() => {
    if (!user) return;
    fetchConnections()
      .then(setConnections)
      .finally(() => setLoading(false));
  }, [user]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setFormLoading(true);
    try {
      const conn = await createConnection(form.name, form.connection_string);
      setConnections((prev) => [...prev, conn]);
      setForm({ name: "", connection_string: "" });
      setShowForm(false);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to add connection");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Remove this connection?")) return;
    await deleteConnection(id).catch(() => {});
    setConnections((prev) => prev.filter((c) => c.id !== id));
  }

  async function handleTest(id: string) {
    setTestResults((prev) => ({ ...prev, [id]: { status: "loading", message: "Testing…" } }));
    const result = await testConnection(id).catch((e) => ({
      status: "error",
      message: e instanceof Error ? e.message : "Test failed",
    }));
    setTestResults((prev) => ({ ...prev, [id]: result }));
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
      <div className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to analyst
        </Link>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold text-zinc-100">Database Connections</h1>
            <p className="text-xs text-zinc-500 mt-1">Connect your own PostgreSQL databases</p>
          </div>
          <button
            onClick={() => setShowForm((s) => !s)}
            className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Connection
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 mb-5 space-y-4"
          >
            <h2 className="text-sm font-semibold text-zinc-200">New Connection</h2>
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Display name</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="My Production DB"
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">PostgreSQL connection string</label>
              <input
                required
                type="password"
                value={form.connection_string}
                onChange={(e) => setForm((f) => ({ ...f, connection_string: e.target.value }))}
                placeholder="postgresql://user:password@host:5432/dbname"
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors font-mono"
              />
              <p className="text-xs text-zinc-600 mt-1.5">Stored encrypted — we never expose your credentials</p>
            </div>
            {formError && (
              <p className="text-xs text-red-400 bg-red-950/40 border border-red-900/50 rounded-lg px-3 py-2">
                {formError}
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={formLoading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
              >
                {formLoading ? "Testing & saving…" : "Save connection"}
              </button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setFormError(""); }}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        <div className="space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
            </div>
          ) : connections.length === 0 ? (
            <div className="text-center py-12 text-zinc-500 text-sm">No connections yet</div>
          ) : (
            connections.map((conn) => {
              const testResult = testResults[conn.id];
              return (
                <div
                  key={conn.id}
                  className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-4"
                >
                  <div className="p-2 rounded-lg bg-zinc-800">
                    <Database className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-200 truncate">{conn.name}</span>
                      {conn.is_demo && (
                        <span className="text-xs px-1.5 py-0.5 bg-blue-950 text-blue-400 rounded border border-blue-900/50">
                          Demo
                        </span>
                      )}
                      {!conn.is_active && (
                        <span className="text-xs px-1.5 py-0.5 bg-zinc-800 text-zinc-500 rounded">Inactive</span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-500 mt-0.5">{conn.db_type}</p>
                    {testResult && (
                      <div className={`flex items-center gap-1.5 mt-1.5 text-xs ${
                        testResult.status === "ok" ? "text-green-400" :
                        testResult.status === "loading" ? "text-zinc-400" : "text-red-400"
                      }`}>
                        {testResult.status === "ok" && <CheckCircle className="w-3 h-3" />}
                        {testResult.status === "error" && <XCircle className="w-3 h-3" />}
                        {testResult.status === "loading" && <Loader2 className="w-3 h-3 animate-spin" />}
                        {testResult.message}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleTest(conn.id)}
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
                    >
                      Test
                    </button>
                    {!conn.is_demo && (
                      <button
                        onClick={() => handleDelete(conn.id)}
                        className="p-1.5 text-zinc-600 hover:text-red-400 transition-colors"
                        title="Remove"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
