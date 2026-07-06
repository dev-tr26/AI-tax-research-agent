"use client";

import { useEffect, useState } from "react";
import {
  Search, Brain, CheckCircle2, User, Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { StreamStage } from "@/types";

interface PipelineStatusProps {
  stage: StreamStage | null;
  message: string;
}

const STAGES: Array<{
  key: StreamStage;
  label: string;
  icon: React.ElementType;
  agentLabel: string;
}> = [
  { key: "session",   label: "Session init",       icon: User,         agentLabel: "UserProxyAgent" },
  { key: "embedding", label: "Query embedding",     icon: Sparkles,     agentLabel: "RetrievalAgent" },
  { key: "retrieval", label: "Corpus retrieval",    icon: Search,       agentLabel: "RetrievalAgent" },
  { key: "synthesis", label: "LLM synthesis",       icon: Brain,        agentLabel: "RetrievalAgent" },
  { key: "validation",label: "Citation validation", icon: CheckCircle2, agentLabel: "CitationValidationAgent" },
];

export function PipelineStatus({ stage, message }: PipelineStatusProps) {
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const id = setInterval(() => setDots((d) => (d.length >= 3 ? "." : d + ".")), 500);
    return () => clearInterval(id);
  }, []);

  const currentIdx = STAGES.findIndex((s) => s.key === stage);

  return (
    <div className="rounded-2xl bg-ink-900/80 border border-ink-800 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-ink-800 flex items-center gap-3">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-gold-400 status-dot"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
        <span className="text-xs font-mono text-ink-400">
          agent pipeline running{dots}
        </span>
        {message && (
          <span className="ml-auto text-xs text-ink-500 italic">{message}</span>
        )}
      </div>

      {/* Stages */}
      <div className="p-4 space-y-2">
        {STAGES.map((s, i) => {
          const isDone = currentIdx > i;
          const isActive = currentIdx === i;
          const isPending = currentIdx < i;
          const Icon = s.icon;

          return (
            <div
              key={s.key}
              className={cn(
                "flex items-center gap-3 p-2.5 rounded-lg transition-all duration-300",
                isActive && "bg-gold-500/8 border border-gold-500/20",
                isDone && "opacity-60"
              )}
            >
              <div className={cn(
                "w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                isDone  && "bg-jade-700/40 border border-jade-500/30",
                isActive && "bg-gold-500/20 border border-gold-500/30",
                isPending && "bg-ink-800 border border-ink-700"
              )}>
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-jade-400" />
                ) : (
                  <Icon className={cn(
                    "w-3.5 h-3.5 transition-colors",
                    isActive ? "text-gold-400" : "text-ink-600"
                  )} />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className={cn(
                  "text-xs font-medium leading-tight",
                  isDone   ? "text-ink-400" :
                  isActive ? "text-ink-100" : "text-ink-600"
                )}>
                  {s.label}
                  {isActive && (
                    <span className="ml-2 text-[10px] font-normal text-gold-500 animate-pulse">
                      running
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-ink-600 mt-0.5 font-mono">{s.agentLabel}</div>
              </div>

              {isActive && (
                <div className="flex gap-0.5 flex-shrink-0">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="w-1 h-1 rounded-full bg-gold-400"
                      style={{
                        animation: "statusPulse 1s ease-in-out infinite",
                        animationDelay: `${i * 0.15}s`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Shimmer progress bar */}
      <div className="h-0.5 bg-ink-800 overflow-hidden">
        <div
          className="h-full shimmer-effect"
          style={{ width: `${Math.max(((currentIdx + 1) / STAGES.length) * 100, 15)}%` }}
        />
      </div>
    </div>
  );
}
