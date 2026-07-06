"use client";

import { useState } from "react";
import { ShieldCheck, ShieldAlert, X } from "lucide-react";
import { cn, citationTypeIcon, confidenceBg } from "@/lib/utils";
import type { Citation } from "@/types";

interface CitationInlineProps {
  citation: Citation;
  index: number;
}

export function CitationInline({ citation, index }: CitationInlineProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setExpanded((e) => !e)}
        className={cn(
          "inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded border transition-colors mx-0.5",
          citation.verified
            ? "bg-jade-700/20 border-jade-500/30 text-jade-300 hover:bg-jade-700/35"
            : "bg-gold-500/10 border-gold-500/25 text-gold-400 hover:bg-gold-500/20"
        )}
        title={citation.text}
      >
        {citationTypeIcon(citation.type)}
        <span>{index + 1}</span>
        {citation.verified
          ? <ShieldCheck className="w-2.5 h-2.5" />
          : <ShieldAlert className="w-2.5 h-2.5" />}
      </button>

      {expanded && (
        <span className={cn(
          "absolute z-50 bottom-full left-0 mb-2 w-72 p-3 rounded-xl shadow-2xl border",
          "bg-ink-800 border-ink-700 text-xs",
          "animate-slide-up"
        )}>
          <span className="flex items-start justify-between gap-2 mb-2">
            <span className="font-medium text-ink-100 leading-snug">{citation.text}</span>
            <button
              onClick={(e) => { e.stopPropagation(); setExpanded(false); }}
              className="text-ink-500 hover:text-ink-200 flex-shrink-0"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
          <span className="flex items-center gap-2 flex-wrap">
            <span className={cn(
              "text-[9px] px-1.5 py-0.5 rounded-full border uppercase tracking-wider font-semibold",
              confidenceBg(
                citation.confidence >= 0.8 ? "HIGH"
                : citation.confidence >= 0.55 ? "MEDIUM"
                : "LOW"
              )
            )}>
              {Math.round(citation.confidence * 100)}% confidence
            </span>
            {citation.verified
              ? <span className="text-[9px] text-jade-400 flex items-center gap-1">
                  <ShieldCheck className="w-2.5 h-2.5" />Verified
                </span>
              : <span className="text-[9px] text-gold-400 flex items-center gap-1">
                  <ShieldAlert className="w-2.5 h-2.5" />Unverified
                </span>
            }
          </span>
          {citation.source_chunk_id && (
            <span className="block mt-1.5 text-[9px] font-mono text-ink-600 truncate">
              {citation.source_chunk_id}
            </span>
          )}
          {citation.note && (
            <span className="block mt-1 text-[10px] text-gold-500/70 italic">{citation.note}</span>
          )}
        </span>
      )}
    </span>
  );
}
