import type {
  QueryResult,
  StreamStatusEvent,
  SessionHistory,
  Session,
  MetricsSummary,
  IngestionStats,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Query ────────────────────────────────────────────────────────────────────

export async function submitQuery(
  query: string,
  sessionId?: string
): Promise<QueryResult> {
  return apiFetch<QueryResult>("/query", {
    method: "POST",
    body: JSON.stringify({ query, session_id: sessionId ?? null, stream: false }),
  });
}

export type StreamCallback = {
  onStatus: (event: StreamStatusEvent) => void;
  onResult: (result: QueryResult) => void;
  onError: (msg: string) => void;
  onDone: (sessionId: string) => void;
};

export function streamQuery(
  query: string,
  sessionId: string | undefined,
  callbacks: StreamCallback
): () => void {
  const controller = new AbortController();

  fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId ?? null, stream: true }),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.ok || !res.body) {
      callbacks.onError(`HTTP ${res.status}`);
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const lines = part.trim().split("\n");
        const eventLine = lines.find((l) => l.startsWith("event:"));
        const dataLine = lines.find((l) => l.startsWith("data:"));
        if (!eventLine || !dataLine) continue;

        const event = eventLine.replace("event:", "").trim();
        const rawData = dataLine.replace("data:", "").trim();

        try {
          const data = JSON.parse(rawData);
          if (event === "status") callbacks.onStatus(data as StreamStatusEvent);
          else if (event === "result") callbacks.onResult(data as QueryResult);
          else if (event === "done") callbacks.onDone(data.session_id);
          else if (event === "error") callbacks.onError(data.message);
        } catch {
          // malformed chunk — skip
        }
      }
    }
  }).catch((err) => {
    if (err.name !== "AbortError") callbacks.onError(String(err));
  });

  return () => controller.abort();
}

// ─── Sessions ─────────────────────────────────────────────────────────────────

export async function fetchSessions(limit = 20): Promise<Session[]> {
  return apiFetch<Session[]>(`/sessions?limit=${limit}`);
}

export async function fetchSessionHistory(sessionId: string): Promise<SessionHistory> {
  return apiFetch<SessionHistory>(`/sessions/${sessionId}/history`);
}

// ─── Metrics ──────────────────────────────────────────────────────────────────

export async function fetchMetrics(): Promise<MetricsSummary> {
  return apiFetch<MetricsSummary>("/metrics");
}

// ─── Ingestion ────────────────────────────────────────────────────────────────

export async function fetchIngestionStats(): Promise<IngestionStats> {
  return apiFetch<IngestionStats>("/ingest/stats");
}

export async function triggerIngestion(source: "all" | "ita" | "cbdt") {
  return apiFetch("/ingest", {
    method: "POST",
    body: JSON.stringify({ source }),
  });
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/health");
}
