"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ChevronDown, ChevronUp, Clock, Layers,
  FileText, Copy, Check,
} from "lucide-react";
import { CitationPanel } from "@/components/citations/CitationPanel";
import { LatencyBadge } from "./LatencyBadge";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { cn, formatMs } from "@/lib/utils";
import type { QueryResult } from "@/types";

interface ResponseDisplayProps {
  result: QueryResult;
}

export function ResponseDisplay({ result }: ResponseDisplayProps) {
  const [chunksOpen, setChunksOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { response, timings, top_chunks } = result;

  async function copyMarkdown() {
    await navigator.clipboard.writeText(response.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Main answer card */}
      <div className="rounded-2xl bg-ink-900/60 border border-ink-800 overflow-hidden">
        {/* Card header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-ink-800/80 bg-ink-900/40">
          <div className="flex items-center gap-3">
            <ConfidenceBadge level={response.confidence} />
            {response.unverified_count > 0 && (
              <span className="text-[10px] bg-gold-500/10 border border-gold-500/25 text-gold-400 px-2 py-0.5 rounded-full">
                {response.unverified_count} unverified citation{response.unverified_count > 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <LatencyBadge ms={response.latency_ms} />
            <button
              onClick={copyMarkdown}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-ink-500 hover:text-ink-200 hover:bg-ink-700 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-jade-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Markdown response */}
        <div className="px-6 py-5 markdown-content">
          <pre className="text-red-400 whitespace-pre-wrap break-words">
            {response.markdown}
          </pre>
        </div>
      </div>

      {/* Citation panel */}
      {response.citations.length > 0 && (
        <CitationPanel citations={response.citations} />
      )}

      {/* Timing breakdown */}
      <TimingBreakdown timings={timings} />

      {/* Retrieved chunks (collapsible) */}
      {top_chunks && top_chunks.length > 0 && (
        <div className="rounded-xl border border-ink-800 overflow-hidden">
          <button
            onClick={() => setChunksOpen((o) => !o)}
            className="w-full flex items-center justify-between px-4 py-3 bg-ink-900/40 hover:bg-ink-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-ink-500" />
              <span className="text-xs text-ink-400 font-medium">
                {top_chunks.length} Retrieved Chunks
              </span>
            </div>
            {chunksOpen
              ? <ChevronUp className="w-3.5 h-3.5 text-ink-600" />
              : <ChevronDown className="w-3.5 h-3.5 text-ink-600" />}
          </button>
          {chunksOpen && (
            <div className="divide-y divide-ink-800/60">
              {top_chunks.map((chunk, i) => (
                <ChunkPreview key={chunk.chunk_id} chunk={chunk} index={i} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TimingBreakdown({ timings }: { timings: QueryResult["timings"] }) {
  const stages = [
    { label: "Embed",    ms: timings.embedding_ms,          color: "bg-azure-500" },
    { label: "Vector",   ms: timings.vector_retrieval_ms,   color: "bg-gold-400" },
    { label: "Rerank",   ms: timings.rerank_ms,             color: "bg-gold-600" },
    { label: "LLM",      ms: timings.synthesis_ms,          color: "bg-jade-500" },
    { label: "Cite Val", ms: timings.citation_validation_ms,color: "bg-ruby-400" },
  ].filter((s) => s.ms > 0);

  const total = timings.total_ms || 1;

  return (
    <div className="rounded-xl bg-ink-900/40 border border-ink-800 px-4 py-3">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="w-3.5 h-3.5 text-ink-500" />
        <span className="text-[10px] font-mono text-ink-500 uppercase tracking-wider">
          Pipeline latency — {formatMs(timings.total_ms)}
        </span>
      </div>
      {/* Stacked bar */}
      <div className="flex h-2 rounded-full overflow-hidden gap-px mb-2">
        {stages.map((s) => (
          <div
            key={s.label}
            className={cn("h-full rounded-sm transition-all", s.color)}
            style={{ width: `${(s.ms / total) * 100}%` }}
          />
        ))}
      </div>
      {/* Labels */}
      <div className="flex flex-wrap gap-3">
        {stages.map((s) => (
          <div key={s.label} className="flex items-center gap-1.5">
            <span className={cn("w-2 h-2 rounded-sm flex-shrink-0", s.color)} />
            <span className="text-[10px] text-ink-500">{s.label}</span>
            <span className="text-[10px] text-ink-400 font-mono">{formatMs(s.ms)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChunkPreview({
  chunk, index,
}: { chunk: QueryResult["top_chunks"][number]; index: number }) {
  const meta = chunk.metadata;
  return (
    <div className="px-4 py-3 bg-ink-900/20 hover:bg-ink-800/30 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono text-ink-600">#{index + 1}</span>
          <code className="text-[10px] text-gold-500/80 bg-gold-500/8 px-1.5 py-0.5 rounded font-mono">
            {chunk.chunk_id}
          </code>
          {meta.section && (
            <span className="text-[10px] text-ink-500">{meta.section}</span>
          )}
          {meta.circular_number && (
            <span className="text-[10px] text-azure-400">Circular {meta.circular_number}</span>
          )}
        </div>
        <span className="text-[10px] font-mono text-ink-600 flex-shrink-0">
          score {Number(chunk.score).toFixed(3)}
        </span>
      </div>
      <p className="text-xs text-ink-400 leading-relaxed line-clamp-3">
        {chunk.text}
      </p>
    </div>
  );
}
