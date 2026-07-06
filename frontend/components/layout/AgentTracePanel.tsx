"use client";

import { useState } from "react";
import {
  GitBranch, User, Search, ShieldCheck,
  ChevronRight, ChevronDown, Clock,
  CheckCircle2, AlertTriangle,
} from "lucide-react";
import { useMetrics } from "@/hooks/useMetrics";
import { formatMs, cn } from "@/lib/utils";

const AGENTS = [
  {
    name: "UserProxyAgent",
    icon: User,
    color: "text-azure-400",
    bg: "bg-azure-600/15 border-azure-500/25",
    desc: "Session management, follow-up detection, output formatting",
    timingKey: "user_proxy_ms",
  },
  {
    name: "RetrievalAgent",
    icon: Search,
    color: "text-gold-400",
    bg: "bg-gold-500/10 border-gold-500/20",
    desc: "Embed → vector search → BM25 → RRF merge → rerank → LLM synthesis",
    timingKey: "retrieval_ms",
    subStages: [
      { label: "Query embedding",    key: "embedding_ms",          budget: 200  },
      { label: "Vector retrieval",   key: "vector_retrieval_ms",   budget: 400  },
      { label: "Keyword retrieval",  key: "keyword_retrieval_ms",  budget: 200  },
      { label: "Cross-encoder rerank", key: "rerank_ms",           budget: 300  },
      { label: "LLM synthesis",      key: "synthesis_ms",          budget: 3500 },
    ],
  },
  {
    name: "CitationValidationAgent",
    icon: ShieldCheck,
    color: "text-jade-400",
    bg: "bg-jade-700/15 border-jade-500/25",
    desc: "Scan citations → verify against Pinecone → score confidence → flag hallucinations",
    timingKey: "citation_validation_ms",
  },
];

export function AgentTracePanel() {
  const { metrics, loading } = useMetrics();
  const [selected, setSelected] = useState<string | null>(null);

  const recent = metrics ? undefined : null; // placeholder — real data from metrics

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-ink-800 border border-ink-700 flex items-center justify-center">
          <GitBranch className="w-4.5 h-4.5 text-gold-400" />
        </div>
        <div>
          <h1 className="font-display font-semibold text-ink-100 text-xl">Agent Pipeline</h1>
          <p className="text-xs text-ink-500 mt-0.5">AutoGen three-agent execution trace and architecture</p>
        </div>
      </div>

      {/* Architecture diagram */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Pipeline Architecture</h2>
        <div className="flex items-stretch gap-0">
          {AGENTS.map((agent, i) => {
            const Icon = agent.icon;
            const isOpen = selected === agent.name;
            return (
              <div key={agent.name} className="flex items-stretch gap-0 flex-1">
                {/* Agent card */}
                <button
                  onClick={() => setSelected(isOpen ? null : agent.name)}
                  className={cn(
                    "flex-1 text-left p-4 rounded-xl border transition-all duration-200",
                    isOpen ? agent.bg : "bg-ink-900/60 border-ink-800 hover:border-ink-700"
                  )}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center",
                      isOpen ? agent.bg : "bg-ink-800 border border-ink-700"
                    )}>
                      <Icon className={cn("w-4 h-4", isOpen ? agent.color : "text-ink-500")} />
                    </div>
                    {isOpen
                      ? <ChevronDown className="w-3.5 h-3.5 text-ink-500" />
                      : <ChevronRight className="w-3.5 h-3.5 text-ink-700" />}
                  </div>
                  <div className={cn("text-xs font-semibold mb-1", isOpen ? agent.color : "text-ink-200")}>
                    {agent.name}
                  </div>
                  <div className="text-[10px] text-ink-500 leading-relaxed">{agent.desc}</div>

                  {/* Sub-stages expanded */}
                  {isOpen && "subStages" in agent && agent.subStages && (
                    <div className="mt-3 space-y-1.5 border-t border-ink-800/60 pt-3">
                      {agent.subStages.map((s) => (
                        <div key={s.key} className="flex items-center justify-between">
                          <span className="text-[10px] text-ink-400">{s.label}</span>
                          <span className="text-[10px] font-mono text-ink-500">
                            target ≤{formatMs(s.budget)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </button>

                {/* Arrow */}
                {i < AGENTS.length - 1 && (
                  <div className="flex items-center px-2 flex-shrink-0">
                    <ChevronRight className="w-4 h-4 text-ink-700" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Latest metrics per agent */}
      {metrics && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold text-ink-400 uppercase tracking-wider">
            Stage Latency — Last {metrics.total_queries} Queries
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Embedding",         p50: metrics.latency.vector_retrieval.p50_ms,  budget: 200,  color: "bg-azure-500" },
              { label: "Vector Retrieval",  p50: metrics.latency.vector_retrieval.p50_ms,  budget: 400,  color: "bg-gold-400" },
              { label: "LLM Synthesis",     p50: metrics.latency.llm_synthesis.p50_ms,     budget: 3500, color: "bg-jade-500" },
              { label: "Citation Validation", p50: metrics.latency.citation_validation.p50_ms, budget: 1000, color: "bg-ruby-400" },
            ].map(({ label, p50, budget, color }) => {
              const pct = Math.min((p50 / budget) * 100, 100);
              const over = p50 > budget;
              return (
                <div key={label} className="rounded-xl bg-ink-900/60 border border-ink-800 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-ink-300">{label}</span>
                    <span className={cn(
                      "text-[9px] font-mono px-1.5 py-0.5 rounded border",
                      over ? "text-ruby-300 bg-ruby-700/15 border-ruby-500/25"
                           : "text-jade-300 bg-jade-700/15 border-jade-500/25"
                    )}>
                      P50 {formatMs(p50)}
                    </span>
                  </div>
                  <div className="h-1.5 bg-ink-800 rounded-full overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all", over ? "bg-ruby-500" : color)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-[9px] text-ink-700">0</span>
                    <span className="text-[9px] text-ink-700">budget {formatMs(budget)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Citation quality */}
      {metrics && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Citation Verification</h2>
          <div className="rounded-xl bg-ink-900/60 border border-ink-800 p-5">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <Stat label="Total Citations" value={metrics.quality.total_citations} />
              <Stat label="Verified"        value={metrics.quality.verified_citations} good />
              <Stat
                label="Hallucination Rate"
                value={`${(metrics.quality.hallucination_rate * 100).toFixed(1)}%`}
                bad={metrics.quality.hallucination_rate > 0.05}
              />
            </div>
            {/* Pass/fail for < 5% target */}
            <div className={cn(
              "flex items-center gap-2 text-xs px-3 py-2 rounded-lg border",
              metrics.quality.hallucination_rate <= 0.05
                ? "bg-jade-700/15 border-jade-500/25 text-jade-300"
                : "bg-ruby-700/15 border-ruby-500/25 text-ruby-300"
            )}>
              {metrics.quality.hallucination_rate <= 0.05
                ? <CheckCircle2 className="w-3.5 h-3.5" />
                : <AlertTriangle className="w-3.5 h-3.5" />}
              Hallucination rate target: &lt;5%
              {metrics.quality.hallucination_rate <= 0.05 ? " ✓ PASS" : " ✗ EXCEEDS TARGET"}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function Stat({
  label, value, good, bad,
}: { label: string; value: string | number; good?: boolean; bad?: boolean }) {
  return (
    <div className="text-center">
      <div className={cn(
        "text-xl font-display font-semibold",
        good ? "text-jade-300" : bad ? "text-ruby-300" : "text-ink-100"
      )}>
        {value}
      </div>
      <div className="text-[10px] text-ink-500 uppercase tracking-wider mt-0.5">{label}</div>
    </div>
  );
}
