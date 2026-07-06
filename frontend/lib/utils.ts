import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ConfidenceLevel } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  }).format(new Date(iso));
}

export function confidenceColor(level: ConfidenceLevel): string {
  switch (level) {
    case "HIGH":   return "text-jade-300";
    case "MEDIUM": return "text-gold-300";
    case "LOW":    return "text-ruby-400";
    default:       return "text-ink-400";
  }
}

export function confidenceBg(level: ConfidenceLevel): string {
  switch (level) {
    case "HIGH":   return "bg-jade-700/30 border-jade-500/40 text-jade-300";
    case "MEDIUM": return "bg-gold-600/20 border-gold-500/40 text-gold-300";
    case "LOW":    return "bg-ruby-700/20 border-ruby-500/40 text-ruby-400";
    default:       return "bg-ink-700/30 border-ink-500/40 text-ink-300";
  }
}

export function citationTypeIcon(type: string): string {
  switch (type) {
    case "act":      return "§";
    case "circular": return "⊛";
    case "case":     return "⚖";
    default:         return "•";
  }
}

export function truncate(str: string, max: number): string {
  if (str.length <= max) return str;
  return str.slice(0, max - 1) + "…";
}

export function slugify(str: string): string {
  return str.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}
