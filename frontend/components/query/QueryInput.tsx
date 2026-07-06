"use client";

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { Send, Loader2, Mic, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface QueryInputProps {
  onSubmit: (query: string, stream?: boolean) => void;
  loading: boolean;
  isFollowUp?: boolean;
}

const PLACEHOLDER_LINES = [
  "Is exemption under Section 54 available for pre-purchase of a new property?",
  "Explain deemed dividend under Section 2(22)(e) with case law…",
  "What are the conditions for Section 80C deduction?",
  "Burden of proof under Section 68 for cash credits…",
];

export function QueryInput({ onSubmit, loading, isFollowUp }: QueryInputProps) {
  const [value, setValue] = useState("");
  const [placeholderIdx] = useState(() => Math.floor(Math.random() * PLACEHOLDER_LINES.length));
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const q = value.trim();
    if (!q || loading) return;
    onSubmit(q, true);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, loading, onSubmit]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const charCount = value.length;
  const nearLimit = charCount > 800;

  return (
    <div className={cn(
      "relative rounded-2xl border transition-all duration-200",
      loading
        ? "border-gold-500/30 bg-ink-900/60"
        : "border-ink-700 bg-ink-900 hover:border-ink-600 focus-within:border-gold-500/50 focus-within:shadow-[0_0_0_3px_rgba(232,185,48,0.08)]"
    )}>
      {isFollowUp && (
        <div className="px-4 pt-2.5 pb-0">
          <span className="text-[10px] font-mono text-gold-500/70 bg-gold-500/8 px-2 py-0.5 rounded-full border border-gold-500/20">
            follow-up — context preserved
          </span>
        </div>
      )}

      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        disabled={loading}
        rows={1}
        className={cn(
          "w-full resize-none bg-transparent text-ink-100 text-sm leading-relaxed",
          "px-4 py-3 outline-none placeholder:text-ink-600",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "font-body"
        )}
        placeholder={PLACEHOLDER_LINES[placeholderIdx]}
        style={{ minHeight: "52px", maxHeight: "200px" }}
      />

      {/* Bottom bar */}
      <div className="flex items-center justify-between px-4 pb-3">
        <div className="flex items-center gap-3">
          {nearLimit && (
            <span className={cn(
              "text-[10px] font-mono",
              charCount > 1000 ? "text-ruby-400" : "text-gold-500/70"
            )}>
              {charCount}/1000
            </span>
          )}
          <span className="text-[10px] text-ink-700 hidden sm:inline">
            ↵ to submit · Shift+↵ for newline
          </span>
        </div>

        <div className="flex items-center gap-2">
          {value && !loading && (
            <button
              onClick={() => setValue("")}
              className="w-6 h-6 rounded-full flex items-center justify-center text-ink-500 hover:text-ink-300 hover:bg-ink-700 transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!value.trim() || loading}
            className={cn(
              "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200",
              value.trim() && !loading
                ? "bg-gold-500 text-ink-950 hover:bg-gold-400 shadow-[0_2px_12px_rgba(232,185,48,0.3)]"
                : "bg-ink-800 text-ink-500 cursor-not-allowed"
            )}
          >
            {loading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            {loading ? "Researching…" : "Research"}
          </button>
        </div>
      </div>
    </div>
  );
}
