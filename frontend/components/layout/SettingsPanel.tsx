"use client";

import { useState } from "react";
import {
  Settings, Zap, Database, CheckCircle2, XCircle,
  RefreshCw, Play, Loader2, BarChart2,
} from "lucide-react";
import { useMetrics, useIngestionStats } from "@/hooks/useMetrics";
import { triggerIngestion } from "@/lib/api";
import { formatMs, cn } from "@/lib/utils";
import type { ConfidenceLevel } from "@/types";

export function SettingsPanel() {
  const { metrics, loading: mLoading, refresh } = useMetrics(30000);
  const { stats, loading: sLoading } = useIngestionStats();
  const [ingestSource, setIngestSource] = useState<"all" | "ita" | "cbdt">("all");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestMsg, setIngestMsg] = useState("");

  async function handleIngest() {
    setIngestLoading(true);
    setIngestMsg("");
    try {
      const r = await triggerIngestion(ingestSource) as { job_id: string };
      setIngestMsg(`Ingestion started — job ${r.job_id.slice(0, 8)}`);
    } catch (e) {
      setIngestMsg(`Error: ${e}`);
    } finally {
      setIngestLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-ink-800 border border-ink-700 flex items-center justify-center">
          <Settings className="w-4.5 h-4.5 text-gold-400" />
        </div>
        <div>
          <h1 className="font-display font-semibold text-ink-100 text-xl">Settings & Monitoring</h1>
          <p className="text-xs text-ink-500 mt-0.5">Pipeline metrics, SLA compliance, and ingestion controls</p>
        </div>
      </div>

      {/* SLA Compliance */}
      {metrics && (
        <section className="space-y-3">
          <SectionHeader icon={<Zap className="w-4 h-4 text-gold-400" />} title="SLA Compliance" />
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(metrics.sla_compliance).map(([key, pass]) => (
              <SLACard key={key} label={slaLabel(key)} pass={pass as boolean} />
            ))}
          </div>
        </section>
      )}

      {/* Latency */}
      {metrics && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <SectionHeader icon={<BarChart2 className="w-4 h-4 text-gold-400" />} title="Latency Breakdown" />
            <button
              onClick={refresh}
              className="flex items-center gap-1.5 text-xs text-ink-400 hover:text-gold-400 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(metrics.latency).map(([stage, data]) => (
              <LatencyCard
                key={stage}
                title={stageLabel(stage)}
                p50={data.p50_ms}
                p95={data.p95_ms}
                mean={data.mean_ms}
                threshold={stageThreshold(stage)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Quality */}
      {metrics && (
        <section className="space-y-3">
          <SectionHeader icon={<CheckCircle2 className="w-4 h-4 text-gold-400" />} title="Citation Quality" />
          <div className="grid grid-cols-3 gap-3">
            <MetricTile
              label="Total Queries"
              value={metrics.total_queries}
            />
            <MetricTile
              label="Hallucination Rate"
              value={`${(metrics.quality.hallucination_rate * 100).toFixed(1)}%`}
              highlight={metrics.quality.hallucination_rate > 0.05 ? "bad" : "good"}
            />
            <MetricTile
              label="Verified Citations"
              value={`${metrics.quality.verified_citations}/${metrics.quality.total_citations}`}
            />
          </div>
          {/* Confidence distribution */}
          <div className="rounded-xl bg-ink-900 border border-ink-800 p-4">
            <div className="text-xs text-ink-400 mb-3 font-medium">Confidence Distribution</div>
            <div className="flex gap-3">
              {(["HIGH", "MEDIUM", "LOW"] as ConfidenceLevel[]).map((level) => {
                const count = metrics.quality.confidence_distribution[level] ?? 0;
                const total = metrics.total_queries || 1;
                const pct = Math.round((count / total) * 100);
                const colors = { HIGH: "bg-jade-500", MEDIUM: "bg-gold-400", LOW: "bg-ruby-500" };
                return (
                  <div key={level} className="flex-1">
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-ink-400">{level}</span>
                      <span className="text-ink-300">{pct}%</span>
                    </div>
                    <div className="h-1.5 bg-ink-800 rounded-full overflow-hidden">
                      <div
                        className={cn("h-full rounded-full transition-all", colors[level])}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* Ingestion */}
      <section className="space-y-3">
        <SectionHeader icon={<Database className="w-4 h-4 text-gold-400" />} title="Document Ingestion" />
        <div className="rounded-xl bg-ink-900 border border-ink-800 p-5 space-y-4">
          {stats && !sLoading && (
            <div className="grid grid-cols-3 gap-3 pb-4 border-b border-ink-800">
              {Object.entries(stats.ingestion ?? {}).map(([status, count]) => (
                <div key={status} className="text-center">
                  <div className="text-lg font-display font-semibold text-ink-100">{count}</div>
                  <div className="text-[10px] text-ink-500 uppercase tracking-wider mt-0.5">{status}</div>
                </div>
              ))}
            </div>
          )}

          <div>
            <label className="block text-xs text-ink-400 mb-2 font-medium">Ingestion Source</label>
            <div className="flex gap-2">
              {(["all", "ita", "cbdt"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setIngestSource(s)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                    ingestSource === s
                      ? "bg-gold-500/15 border-gold-500/40 text-gold-300"
                      : "bg-ink-800 border-ink-700 text-ink-400 hover:text-ink-200"
                  )}
                >
                  {s === "all" ? "All Sources" : s === "ita" ? "ITA 2025" : "CBDT Circulars"}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleIngest}
            disabled={ingestLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gold-500/10 border border-gold-500/30 text-gold-300 hover:bg-gold-500/20 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {ingestLoading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Play className="w-4 h-4" />}
            Trigger Ingestion
          </button>

          {ingestMsg && (
            <p className="text-xs text-jade-300 font-mono">{ingestMsg}</p>
          )}
        </div>
      </section>

      {mLoading && (
        <div className="text-center text-xs text-ink-500 flex items-center justify-center gap-2">
          <Loader2 className="w-3 h-3 animate-spin" />
          Loading metrics…
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2">
      {icon}
      <h2 className="font-display font-semibold text-ink-200 text-sm">{title}</h2>
    </div>
  );
}

function SLACard({ label, pass }: { label: string; pass: boolean }) {
  return (
    <div className={cn(
      "flex items-center justify-between p-3.5 rounded-xl border transition-colors",
      pass
        ? "bg-jade-700/10 border-jade-500/25"
        : "bg-ruby-700/10 border-ruby-500/25"
    )}>
      <span className="text-xs text-ink-300">{label}</span>
      {pass
        ? <CheckCircle2 className="w-4 h-4 text-jade-400" />
        : <XCircle className="w-4 h-4 text-ruby-400" />}
    </div>
  );
}

function LatencyCard({
  title, p50, p95, mean, threshold,
}: { title: string; p50: number; p95: number; mean: number; threshold: number }) {
  const over = mean > threshold;
  return (
    <div className="rounded-xl bg-ink-900 border border-ink-800 p-4 space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-ink-300">{title}</span>
        <span className={cn(
          "text-[9px] px-1.5 py-0.5 rounded border font-mono",
          over ? "bg-ruby-700/20 border-ruby-500/30 text-ruby-300" : "bg-jade-700/20 border-jade-500/30 text-jade-300"
        )}>
          {over ? "ABOVE TARGET" : "ON TARGET"}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {[["P50", p50], ["P95", p95], ["Mean", mean]].map(([label, val]) => (
          <div key={label as string} className="text-center">
            <div className="text-xs font-mono font-semibold text-ink-100">{formatMs(val as number)}</div>
            <div className="text-[9px] text-ink-600 mt-0.5">{label}</div>
          </div>
        ))}
      </div>
      {/* Bar */}
      <div className="h-1 bg-ink-800 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", over ? "bg-ruby-500" : "bg-jade-500")}
          style={{ width: `${Math.min((mean / threshold) * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}

function MetricTile({
  label, value, highlight,
}: { label: string; value: string | number; highlight?: "good" | "bad" }) {
  return (
    <div className="rounded-xl bg-ink-900 border border-ink-800 p-4 text-center">
      <div className={cn(
        "text-xl font-display font-semibold",
        highlight === "good" ? "text-jade-300" : highlight === "bad" ? "text-ruby-300" : "text-ink-100"
      )}>
        {value}
      </div>
      <div className="text-[10px] text-ink-500 mt-1 uppercase tracking-wider">{label}</div>
    </div>
  );
}

function slaLabel(key: string): string {
  const map: Record<string, string> = {
    p50_under_5s: "P50 < 5 seconds",
    p95_under_10s: "P95 < 10 seconds",
    vec_mean_under_800ms: "Vector Retrieval < 800ms",
    cite_mean_under_1s: "Citation Validation < 1s",
  };
  return map[key] ?? key;
}

function stageLabel(key: string): string {
  const map: Record<string, string> = {
    end_to_end: "End-to-End",
    vector_retrieval: "Vector Retrieval",
    citation_validation: "Citation Validation",
    llm_synthesis: "LLM Synthesis",
  };
  return map[key] ?? key;
}

function stageThreshold(key: string): number {
  const map: Record<string, number> = {
    end_to_end: 5000,
    vector_retrieval: 800,
    citation_validation: 1000,
    llm_synthesis: 3500,
  };
  return map[key] ?? 5000;
}
