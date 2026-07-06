// ── Citation ────────────────────────────────────────────────────────────────

export type CitationType = "act" | "circular" | "case";
export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

export interface Citation {
  text: string;
  type: CitationType;
  verified: boolean;
  confidence: number;
  source_chunk_id: string | null;
  note?: string;
  section?: string;
  sub_section?: string;
  circular_number?: string;
}

// ── Query Response ───────────────────────────────────────────────────────────

export interface ResponsePayload {
  markdown: string;
  final_answer: string;
  legal_reasoning: string;
  supporting_references: string;
  confidence: ConfidenceLevel;
  citations: Citation[];
  unverified_count: number;
  latency_ms: number;
}

export interface Timings {
  user_proxy_ms: number;
  retrieval_ms: number;
  embedding_ms: number;
  vector_retrieval_ms: number;
  keyword_retrieval_ms: number;
  rerank_ms: number;
  synthesis_ms: number;
  citation_validation_ms: number;
  total_ms: number;
}

export interface ChunkPreview {
  chunk_id: string;
  text: string;
  metadata: Record<string, string | boolean | number>;
  score: number;
}

export interface QueryResult {
  session_id: string;
  query: string;
  response: ResponsePayload;
  timings: Timings;
  top_chunks: ChunkPreview[];
}

// ── SSE Stream Events ────────────────────────────────────────────────────────

export type StreamStage =
  | "session"
  | "embedding"
  | "retrieval"
  | "synthesis"
  | "validation"
  | "done"
  | "error";

export interface StreamStatusEvent {
  stage: StreamStage;
  message: string;
}

// ── Session / History ────────────────────────────────────────────────────────

export interface Message {
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  confidence: ConfidenceLevel;
}

export interface Session {
  session_id: string;
  created_at: string;
  updated_at: string;
}

export interface SessionHistory {
  session_id: string;
  messages: Message[];
}

// ── Metrics ──────────────────────────────────────────────────────────────────

export interface LatencyBucket {
  p50_ms: number;
  p75_ms?: number;
  p95_ms: number;
  p99_ms?: number;
  mean_ms: number;
}

export interface MetricsSummary {
  total_queries: number;
  error_count: number;
  error_rate: number;
  latency: {
    end_to_end: LatencyBucket;
    vector_retrieval: LatencyBucket;
    citation_validation: LatencyBucket;
    llm_synthesis: LatencyBucket;
  };
  quality: {
    total_citations: number;
    verified_citations: number;
    hallucination_rate: number;
    confidence_distribution: Record<ConfidenceLevel, number>;
  };
  sla_compliance: {
    p50_under_5s: boolean;
    p95_under_10s: boolean;
    vec_mean_under_800ms: boolean;
    cite_mean_under_1s: boolean;
  };
}

// ── Ingestion ────────────────────────────────────────────────────────────────

export interface IngestionStats {
  ingestion: Record<string, number>;
  pinecone?: {
    namespaces?: Record<string, { vector_count: number }>;
    total_vector_count?: number;
  };
}
