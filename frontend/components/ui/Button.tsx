import { forwardRef, ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  leftIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, leftIcon, children, disabled, ...props }, ref) => {
    const base = "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-400 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
      primary:   "bg-gold-500 text-ink-950 hover:bg-gold-400 shadow-[0_2px_12px_rgba(232,185,48,0.25)]",
      secondary: "bg-ink-800 text-ink-200 border border-ink-700 hover:bg-ink-700 hover:text-ink-100",
      ghost:     "text-ink-400 hover:text-ink-100 hover:bg-ink-800",
      danger:    "bg-ruby-600/20 text-ruby-300 border border-ruby-500/30 hover:bg-ruby-600/30",
    };

    const sizes = {
      sm: "text-xs px-3 py-1.5",
      md: "text-sm px-4 py-2",
      lg: "text-base px-5 py-2.5",
    };

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : leftIcon}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
