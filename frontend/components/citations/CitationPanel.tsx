"use client";

import { useState } from "react";
import {
  ShieldCheck, ShieldAlert, BookOpen, FileText,
  Gavel, ChevronDown, ChevronUp, ExternalLink,
} from "lucide-react";
import { cn, citationTypeIcon } from "@/lib/utils";
import type { Citation, CitationType } from "@/types";

interface CitationPanelProps {
  citations: Citation[];
}

export function CitationPanel({ citations }: CitationPanelProps) {
  const [expanded, setExpanded] = useState(true);

  const verified = citations.filter((c) => c.verified);
  const unverified = citations.filter((c) => !c.verified);

  return (
    <div className="rounded-xl border border-ink-800 overflow-hidden">
      {/* Panel header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-4 py-3 bg-ink-900/50 hover:bg-ink-800/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-gold-400" />
          <span className="text-xs font-semibold text-ink-200">
            Citations & Verification
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono bg-jade-700/30 border border-jade-500/30 text-jade-300 px-1.5 py-0.5 rounded-full">
              {verified.length} verified
            </span>
            {unverified.length > 0 && (
              <span className="text-[10px] font-mono bg-gold-500/15 border border-gold-500/30 text-gold-400 px-1.5 py-0.5 rounded-full">
                {unverified.length} unverified
              </span>
            )}
          </div>
        </div>
        {expanded
          ? <ChevronUp className="w-3.5 h-3.5 text-ink-600" />
          : <ChevronDown className="w-3.5 h-3.5 text-ink-600" />}
      </button>

      {expanded && (
        <div className="divide-y divide-ink-800/40">
          {citations.map((citation, i) => (
            <CitationCard key={i} citation={citation} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── CitationCard ──────────────────────────────────────────────────────────────

function CitationCard({ citation }: { citation: Citation }) {
  const isVerified = citation.verified;
  const confidence = citation.confidence;
  const confPct = Math.round(confidence * 100);

  const typeConfig: Record<CitationType, { icon: React.ElementType; label: string; color: string }> = {
    act: {
      icon: BookOpen,
      label: "Act",
      color: "text-azure-400",
    },
    circular: {
      icon: FileText,
      label: "Circular",
      color: "text-gold-400",
    },
    case: {
      icon: Gavel,
      label: "Case Law",
      color: "text-ruby-300",
    },
  };

  const config = typeConfig[citation.type] ?? typeConfig.act;
  const Icon = config.icon;

  return (
    <div className={cn(
      "flex items-start gap-3 px-4 py-3 transition-colors hover:bg-ink-800/20",
      !isVerified && "opacity-70"
    )}>
      {/* Type icon */}
      <div className={cn(
        "w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5",
        isVerified ? "bg-jade-700/25 border border-jade-500/25" : "bg-ink-800 border border-ink-700"
      )}>
        <Icon className={cn("w-3.5 h-3.5", isVerified ? config.color : "text-ink-500")} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={cn(
            "text-xs font-medium leading-snug",
            isVerified ? "text-ink-100" : "text-ink-400 line-through decoration-ink-600"
          )}>
            {citation.text}
          </p>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {isVerified ? (
              <ShieldCheck className="w-3.5 h-3.5 text-jade-400 citation-verified" />
            ) : (
              <ShieldAlert className="w-3.5 h-3.5 text-gold-500" />
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {/* Type badge */}
          <span className={cn(
            "text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded border",
            isVerified
              ? "bg-jade-700/20 border-jade-500/25 text-jade-400"
              : "bg-ink-800 border-ink-700 text-ink-500"
          )}>
            {citationTypeIcon(citation.type)} {config.label}
          </span>

          {/* Confidence bar */}
          <div className="flex items-center gap-1.5">
            <div className="w-16 h-1 bg-ink-800 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  confPct >= 80 ? "bg-jade-400" :
                  confPct >= 55 ? "bg-gold-400" : "bg-ruby-400"
                )}
                style={{ width: `${confPct}%` }}
              />
            </div>
            <span className="text-[9px] font-mono text-ink-600">{confPct}%</span>
          </div>

          {/* Source chunk ID */}
          {citation.source_chunk_id && (
            <span className="text-[9px] font-mono text-ink-700 truncate max-w-[120px]">
              {citation.source_chunk_id}
            </span>
          )}
        </div>

        {/* Note for unverified */}
        {citation.note && (
          <p className="text-[10px] text-gold-500/70 mt-1 italic">{citation.note}</p>
        )}
      </div>
    </div>
  );
}
