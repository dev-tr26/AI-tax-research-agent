"use client";

import { RefreshCw } from "lucide-react";

interface SessionBadgeProps {
  sessionId: string;
  onReset: () => void;
}

export function SessionBadge({ sessionId, onReset }: SessionBadgeProps) {
  return (
    <div className="flex items-center gap-2 bg-ink-900/80 backdrop-blur-sm border border-ink-700 rounded-full px-3 py-1.5 shadow-lg">
      <span className="w-1.5 h-1.5 rounded-full bg-jade-400 status-dot flex-shrink-0" />
      <span className="text-[10px] font-mono text-ink-400">
        {sessionId.slice(0, 8)}…
      </span>
      <button
        onClick={onReset}
        className="text-ink-600 hover:text-gold-400 transition-colors"
        title="New session"
      >
        <RefreshCw className="w-3 h-3" />
      </button>
    </div>
  );
}
