import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  glow?: "gold" | "jade" | "ruby" | "none";
  padding?: "none" | "sm" | "md" | "lg";
}

export function Card({ children, className, glow = "none", padding = "md" }: CardProps) {
  const glows = {
    none: "",
    gold: "glow-gold",
    jade: "glow-jade",
    ruby: "glow-ruby",
  };
  const paddings = {
    none: "",
    sm:   "p-3",
    md:   "p-5",
    lg:   "p-7",
  };

  return (
    <div className={cn(
      "rounded-2xl bg-ink-900/60 border border-ink-800 relative overflow-hidden",
      glows[glow],
      paddings[padding],
      className
    )}>
      {children}
    </div>
  );
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function CardHeader({ children, className }: CardHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between mb-4", className)}>
      {children}
    </div>
  );
}
