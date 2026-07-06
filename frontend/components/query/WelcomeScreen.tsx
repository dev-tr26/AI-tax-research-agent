"use client";

import { Scale, BookOpen, FileText, Gavel, ArrowRight } from "lucide-react";

interface WelcomeScreenProps {
  onSuggestionClick: (query: string) => void;
}

const SUGGESTIONS = [
  {
    icon: BookOpen,
    label: "Section 54 exemption",
    query:
      "Is exemption under Section 54 available if the new residential property is purchased before the date of sale of the original property? Cite the relevant proviso and any CBDT clarification.",
    tag: "Foundational",
  },
  {
    icon: FileText,
    label: "Deemed dividend 2(22)(e)",
    query:
      "LCo. gave a loan to BCo. on 2 April 2023 and the same was repaid on 6 June 2023. BCo. is a shareholder of LCo. and LCo. has sufficient accumulated reserves. Whether deemed dividend provisions under Section 2(22)(e) will apply? Explain with relevant case laws.",
    tag: "Advanced",
  },
  {
    icon: Gavel,
    label: "Burden of proof 68",
    query:
      "A private limited company has been making losses for 5 consecutive years. The Assessing Officer proposes to invoke Section 68 to treat unexplained cash credits as income. What is the burden of proof under Section 68?",
    tag: "Advanced",
  },
  {
    icon: Scale,
    label: "Transfer pricing vs 40A(2)",
    query:
      "A company pays management fees to its foreign parent at 15% of revenue. The AO invokes Section 40A(2)(b) to disallow the excess. How does this interact with Transfer Pricing provisions under Chapter X?",
    tag: "Advanced",
  },
];

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  return (
    <div className="w-full max-w-3xl mx-auto px-6 py-8 animate-fade-in">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-gold-500/20 to-gold-600/10 border border-gold-500/25 mb-5 glow-gold">
          <Scale className="w-7 h-7 text-gold-400" />
        </div>
        <h1 className="font-display text-3xl font-semibold text-ink-100 mb-2 leading-tight">
          Indian Tax Research
        </h1>
        <p className="text-ink-400 text-sm max-w-sm mx-auto leading-relaxed">
          Agentic AI research on the Income Tax Act 2025 and CBDT Circulars.
          Every answer is citation-verified before reaching you.
        </p>
      </div>

      {/* Agent badges */}
      <div className="flex items-center justify-center gap-2 flex-wrap mb-10">
        {["UserProxyAgent", "RetrievalAgent", "CitationValidationAgent"].map((name, i) => (
          <span key={name} className="flex items-center gap-1.5 text-[10px] font-mono text-ink-500 bg-ink-800/70 border border-ink-700 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-gold-500/60" />
            {name}
            {i < 2 && <ArrowRight className="w-2.5 h-2.5 text-ink-700 ml-0.5" />}
          </span>
        ))}
      </div>

      {/* Sample queries */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {SUGGESTIONS.map(({ icon: Icon, label, query, tag }) => (
          <button
            key={label}
            onClick={() => onSuggestionClick(query)}
            className="group text-left p-4 rounded-xl bg-ink-900/60 border border-ink-800 hover:border-gold-500/30 hover:bg-ink-800/60 transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-ink-800 border border-ink-700 group-hover:border-gold-500/30 group-hover:bg-gold-500/8 flex items-center justify-center flex-shrink-0 transition-colors mt-0.5">
                <Icon className="w-4 h-4 text-ink-500 group-hover:text-gold-400 transition-colors" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-ink-200 group-hover:text-ink-100 transition-colors">
                    {label}
                  </span>
                  <span className="text-[9px] text-ink-600 bg-ink-800 px-1.5 py-0.5 rounded font-mono">
                    {tag}
                  </span>
                </div>
                <p className="text-[11px] text-ink-500 leading-relaxed line-clamp-2">
                  {query}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Corpus note */}
      <div className="mt-8 flex items-center justify-center gap-4 text-[10px] text-ink-600">
        <span className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-jade-500" />
          ITA 2025 fully indexed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-jade-500" />
          All CBDT Circulars indexed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-gold-500" />
          BGE-large-en-v1.5 embeddings
        </span>
      </div>
    </div>
  );
}
