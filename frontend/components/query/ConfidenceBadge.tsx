import { ShieldCheck, ShieldAlert, Shield } from "lucide-react";
import { cn, confidenceBg } from "@/lib/utils";
import type { ConfidenceLevel } from "@/types";

interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  showLabel?: boolean;
}

export function ConfidenceBadge({ level, showLabel = true }: ConfidenceBadgeProps) {
  const Icon =
    level === "HIGH" ? ShieldCheck :
    level === "MEDIUM" ? ShieldAlert :
    Shield;

  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider",
      confidenceBg(level)
    )}>
      <Icon className="w-2.5 h-2.5" />
      {showLabel && level}
    </span>
  );
}
