"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@/hooks/useQuery";
import { QueryInput } from "./QueryInput";
import { ResponseDisplay } from "./ResponseDisplay";
import { PipelineStatus } from "./PipelineStatus";
import { WelcomeScreen } from "./WelcomeScreen";
import { SessionBadge } from "./SessionBadge";
import { cn } from "@/lib/utils";

export function QueryInterface() {
  const { result, state, stage, stageMessage, error, sessionId, submit, reset } = useQuery();
  const [history, setHistory] = useState<Array<{ query: string; result: typeof result }>>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // On new result, push to history
  useEffect(() => {
    if (result && state === "done") {
      setHistory((prev) => {
        // avoid duplicate
        if (prev.length > 0 && prev[prev.length - 1].result?.session_id === result.session_id
            && prev[prev.length - 1].query === result.query) return prev;
        return [...prev, { query: result.query, result }];
      });
    }
  }, [result, state]);

  useEffect(() => {
    if (state === "done") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [state]);

  const isIdle = state === "idle" && history.length === 0;

  return (
    <div className="flex flex-col h-full relative">
      {/* Ambient background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-gold-500/3 blur-[120px]" />
        <div className="absolute bottom-1/3 right-0 w-[400px] h-[400px] rounded-full bg-azure-500/3 blur-[100px]" />
      </div>

      {/* Session badge */}
      {sessionId && (
        <div className="absolute top-4 right-4 z-10">
          <SessionBadge sessionId={sessionId} onReset={reset} />
        </div>
      )}

      {/* Content area */}
      <div className={cn(
        "flex-1 overflow-y-auto relative",
        isIdle ? "flex items-center justify-center" : "px-6 py-8 pb-0"
      )}>
        {isIdle ? (
          <WelcomeScreen onSuggestionClick={(q) => submit(q)} />
        ) : (
          <div className="max-w-4xl mx-auto space-y-8">
            {history.map((item, i) => (
              <div key={i} className="animate-slide-up">
                {/* User query bubble */}
                <div className="flex justify-end mb-4">
                  <div className="max-w-xl bg-ink-800/80 border border-ink-700 rounded-2xl rounded-br-md px-4 py-3">
                    <p className="text-sm text-ink-100 leading-relaxed">{item.query}</p>
                  </div>
                </div>
                {/* Response */}
                {item.result && (
                  <ResponseDisplay result={item.result} />
                )}
              </div>
            ))}

            {/* Pipeline status while loading */}
            {(state === "streaming" || state === "loading") && (
              <div className="animate-fade-in">
                <PipelineStatus stage={stage} message={stageMessage} />
              </div>
            )}

            {/* Error */}
            {state === "error" && error && (
              <div className="rounded-xl bg-ruby-700/15 border border-ruby-500/30 p-4 text-sm text-ruby-300 animate-fade-in">
                <strong className="font-semibold">Pipeline error:</strong> {error}
              </div>
            )}

            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Query input — pinned to bottom */}
      <div className={cn(
        "relative z-10 border-t border-ink-800/60 bg-ink-950/80 backdrop-blur-sm",
        isIdle ? "w-full" : ""
      )}>
        <div className="max-w-4xl mx-auto p-4">
          <QueryInput
            onSubmit={submit}
            loading={state === "loading" || state === "streaming"}
            isFollowUp={!!sessionId && history.length > 0}
          />
        </div>
      </div>
    </div>
  );
}
