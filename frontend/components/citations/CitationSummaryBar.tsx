import { ShieldCheck, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Citation } from "@/types";

interface CitationSummaryBarProps {
  citations: Citation[];
}

export function CitationSummaryBar({ citations }: CitationSummaryBarProps) {
  if (!citations.length) return null;

  const verified   = citations.filter((c) => c.verified);
  const unverified = citations.filter((c) => !c.verified);
  const actCount   = citations.filter((c) => c.type === "act").length;
  const circCount  = citations.filter((c) => c.type === "circular").length;
  const caseCount  = citations.filter((c) => c.type === "case").length;

  return (
    <div className="flex items-center gap-3 flex-wrap text-[10px]">
      {verified.length > 0 && (
        <span className="flex items-center gap-1 text-jade-400">
          <ShieldCheck className="w-3 h-3" />
          {verified.length} verified
        </span>
      )}
      {unverified.length > 0 && (
        <span className="flex items-center gap-1 text-gold-400">
          <ShieldAlert className="w-3 h-3" />
          {unverified.length} unverified
        </span>
      )}
      <span className="text-ink-700">·</span>
      {actCount > 0    && <span className="text-azure-400">{actCount} §§</span>}
      {circCount > 0   && <span className="text-gold-400">{circCount} circulars</span>}
      {caseCount > 0   && <span className="text-ruby-300">{caseCount} cases</span>}
    </div>
  );
}
