import { cn } from "@/lib/utils";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Spinner({ size = "md", className }: SpinnerProps) {
  const sizes = { sm: "w-4 h-4 border-2", md: "w-6 h-6 border-2", lg: "w-8 h-8 border-[3px]" };
  return (
    <div
      className={cn(
        "rounded-full border-ink-700 border-t-gold-400 animate-spin",
        sizes[size],
        className
      )}
    />
  );
}

interface SkeletonProps {
  className?: string;
  rows?: number;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div className={cn("rounded-md shimmer-effect bg-ink-800", className)} />
  );
}

export function SkeletonResponse() {
  return (
    <div className="space-y-4 animate-fade-in">
      <div className="rounded-2xl bg-ink-900/60 border border-ink-800 p-6 space-y-4">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/5" />
        <div className="pt-2">
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-3 w-2/3 mt-2" />
        </div>
      </div>
      <div className="rounded-xl bg-ink-900/40 border border-ink-800 p-4 space-y-2">
        <Skeleton className="h-3 w-1/4" />
        <div className="flex gap-2">
          <Skeleton className="h-7 w-32" />
          <Skeleton className="h-7 w-28" />
          <Skeleton className="h-7 w-36" />
        </div>
      </div>
    </div>
  );
}
