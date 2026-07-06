"use client";

import { useState } from "react";
import { Clock, ChevronRight, MessageSquare, Loader2, AlertCircle } from "lucide-react";
import { useSessions, useSessionHistory } from "@/hooks/useSession";
import { formatDate, confidenceBg, cn } from "@/lib/utils";

export function HistoryPanel() {
  const { sessions, loading, error, refresh } = useSessions();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { history, loading: histLoading } = useSessionHistory(selectedId);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 text-gold-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Session list */}
      <div className="w-80 border-r border-ink-800 flex flex-col">
        <div className="p-5 border-b border-ink-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gold-400" />
            <h1 className="font-display font-semibold text-ink-100">Research History</h1>
          </div>
          <button
            onClick={refresh}
            className="text-xs text-ink-400 hover:text-gold-400 transition-colors"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div className="m-3 p-3 rounded-lg bg-ruby-700/20 border border-ruby-500/30 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-ruby-400 flex-shrink-0" />
            <span className="text-xs text-ruby-300">{error}</span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="p-6 text-center text-ink-500 text-sm">
              No sessions yet. Start a research query.
            </div>
          ) : (
            sessions.map((session) => (
              <button
                key={session.session_id}
                onClick={() => setSelectedId(session.session_id)}
                className={cn(
                  "w-full text-left px-4 py-3 border-b border-ink-800/50 hover:bg-ink-800/60 transition-colors flex items-start gap-3 group",
                  selectedId === session.session_id && "bg-gold-500/5 border-l-2 border-l-gold-500"
                )}
              >
                <MessageSquare className="w-3.5 h-3.5 text-ink-500 mt-0.5 flex-shrink-0 group-hover:text-gold-500 transition-colors" />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] font-mono text-ink-400 truncate">
                    {session.session_id.slice(0, 20)}…
                  </div>
                  <div className="text-[10px] text-ink-600 mt-0.5">
                    {formatDate(session.updated_at)}
                  </div>
                </div>
                <ChevronRight className="w-3 h-3 text-ink-700 flex-shrink-0 mt-1 group-hover:text-ink-400 transition-colors" />
              </button>
            ))
          )}
        </div>
      </div>

      {/* Session detail */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selectedId ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3">
            <Clock className="w-10 h-10 text-ink-700" />
            <p className="text-ink-500 text-sm">Select a session to view conversation history</p>
          </div>
        ) : histLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-5 h-5 text-gold-400 animate-spin" />
          </div>
        ) : history ? (
          <div className="max-w-3xl mx-auto space-y-5">
            <div className="flex items-center gap-2 mb-6">
              <h2 className="font-display text-ink-200 text-sm">Session</h2>
              <code className="text-[10px] font-mono text-ink-500 bg-ink-800 px-2 py-0.5 rounded">
                {history.session_id}
              </code>
            </div>

            {history.messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "rounded-xl p-4 border animate-fade-in",
                  msg.role === "user"
                    ? "bg-ink-800/60 border-ink-700"
                    : "bg-ink-900/40 border-ink-800"
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={cn(
                    "text-[10px] font-semibold uppercase tracking-wider",
                    msg.role === "user" ? "text-azure-400" : "text-gold-400"
                  )}>
                    {msg.role === "user" ? "You" : "TaxAI"}
                  </span>
                  {msg.confidence !== "UNKNOWN" && (
                    <span className={cn(
                      "text-[9px] px-2 py-0.5 rounded-full border",
                      confidenceBg(msg.confidence)
                    )}>
                      {msg.confidence}
                    </span>
                  )}
                </div>
                <p className="text-sm text-ink-200 leading-relaxed whitespace-pre-wrap">
                  {msg.content.slice(0, 400)}{msg.content.length > 400 ? "…" : ""}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
