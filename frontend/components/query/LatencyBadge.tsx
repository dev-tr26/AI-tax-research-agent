import { Clock } from "lucide-react";
import { cn, formatMs } from "@/lib/utils";

interface LatencyBadgeProps {
  ms: number;
}

export function LatencyBadge({ ms }: LatencyBadgeProps) {
  const color =
    ms < 4000 ? "text-jade-400" :
    ms < 8000 ? "text-gold-400" :
    "text-ruby-400";

  return (
    <div className={cn("flex items-center gap-1 text-[10px] font-mono", color)}>
      <Clock className="w-2.5 h-2.5" />
      {formatMs(ms)}
    </div>
  );
}
