import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "gold" | "jade" | "ruby" | "azure" | "mono";
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  const variants = {
    default: "bg-ink-800 border-ink-700 text-ink-300",
    gold:    "bg-gold-500/15 border-gold-500/35 text-gold-300",
    jade:    "bg-jade-700/25 border-jade-500/30 text-jade-300",
    ruby:    "bg-ruby-700/20 border-ruby-500/30 text-ruby-300",
    azure:   "bg-azure-600/15 border-azure-400/30 text-azure-300",
    mono:    "bg-ink-900 border-ink-700 text-ink-400 font-mono",
  };

  return (
    <span className={cn(
      "inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider",
      variants[variant],
      className
    )}>
      {children}
    </span>
  );
}
