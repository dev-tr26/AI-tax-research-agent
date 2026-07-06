"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search, Clock, Settings, BookOpen, GitBranch,
  Scale, ChevronRight, Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealth } from "@/hooks/useHealth";

const navItems = [
  { href: "/query",    label: "Research",  icon: Search,   desc: "Ask tax queries"  },
  { href: "/history",  label: "History",   icon: Clock,    desc: "Past sessions"    },
  { href: "/settings", label: "Settings",  icon: Settings, desc: "Config & metrics" },
  { href: "/traces",   label: "Traces",    icon: GitBranch, desc: "Agent pipeline"   },
];

export function Sidebar() {
  const pathname = usePathname();
  const health   = useHealth(30000);

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col bg-ink-900 border-r border-ink-800 relative overflow-visible">
      <div className="absolute -top-24 -left-24 w-64 h-64 rounded-full bg-gold-500/5 blur-3xl pointer-events-none" />

      {/* Logo */}
      <div className="px-6 py-7 border-b border-ink-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold-500 to-gold-600 flex items-center justify-center shadow-lg glow-gold flex-shrink-0">
            <Scale className="w-4 h-4 text-ink-950" />
          </div>
          <div>
            <div className="font-display font-semibold text-ink-50 text-base leading-tight">TaxAI</div>
            <div className="text-[10px] text-ink-400 font-mono uppercase tracking-widest mt-0.5">Direct Tax Research</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon, desc }) => {
          const active = pathname.startsWith(href);
          return (
            <Link key={href} href={href} className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group",
              active ? "bg-gold-500/10 border border-gold-500/20 text-gold-300"
                     : "hover:bg-ink-800 text-ink-300 hover:text-ink-100 border border-transparent"
            )}>
              <Icon className={cn("w-4 h-4 flex-shrink-0 transition-colors",
                active ? "text-gold-400" : "text-ink-500 group-hover:text-ink-300"
              )} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium leading-tight">{label}</div>
                <div className="text-[10px] text-ink-500 group-hover:text-ink-400 transition-colors">{desc}</div>
              </div>
              {active && <ChevronRight className="w-3 h-3 text-gold-500 flex-shrink-0" />}
            </Link>
          );
        })}
      </nav>

      {/* Corpus badge */}
      <div className="mx-3 mb-4 p-3 rounded-lg bg-ink-800/60 border border-ink-700">
        <div className="flex items-center gap-2 mb-2">
          <BookOpen className="w-3.5 h-3.5 text-gold-500" />
          <span className="text-[11px] font-semibold text-ink-300 uppercase tracking-wider">Indexed Corpus</span>
        </div>
        <div className="space-y-1.5">
          {[["Income Tax Act, 2025","indexed"],["CBDT Circulars","indexed"]].map(([label, status]) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-[10px] text-ink-400">{label}</span>
              <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0",
                status === "indexed" ? "bg-jade-400" : "bg-ink-500"
              )} />
            </div>
          ))}
        </div>
      </div>

      {/* System status */}
      <div className="px-4 pb-5 pt-1">
        <div className="flex items-center gap-2">
          <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0",
            health === "online"  ? "bg-jade-400 status-dot" :
            health === "offline" ? "bg-ruby-500" :
            "bg-gold-400 status-dot"
          )} />
          <span className={cn("text-[10px] font-mono",
            health === "online"  ? "text-ink-500" :
            health === "offline" ? "text-ruby-400" : "text-gold-500"
          )}>
            {health === "checking" ? "connecting..." : health === "online" ? "System operational" : "Backend offline"}
          </span>
        </div>
        <div className="mt-1 flex items-center gap-1 text-[10px] text-ink-600">
          <Activity className="w-2.5 h-2.5" />
          <span>Llama 3.3 70B · BGE-large</span>
        </div>
      </div>
    </aside>
  );
}
