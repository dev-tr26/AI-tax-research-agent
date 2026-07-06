"use client";

import { useState, useCallback, useRef } from "react";
import { streamQuery, submitQuery } from "@/lib/api";
import type { QueryResult, StreamStage } from "@/types";

export type QueryState = "idle" | "loading" | "streaming" | "done" | "error";

export interface UseQueryReturn {
  result: QueryResult | null;
  state: QueryState;
  stage: StreamStage | null;
  stageMessage: string;
  error: string | null;
  sessionId: string | undefined;
  submit: (query: string, useStream?: boolean) => Promise<void>;
  reset: () => void;
}

export function useQuery(initialSessionId?: string): UseQueryReturn {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [state, setState] = useState<QueryState>("idle");
  const [stage, setStage] = useState<StreamStage | null>(null);
  const [stageMessage, setStageMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const cancelRef = useRef<(() => void) | null>(null);

  const reset = useCallback(() => {
    cancelRef.current?.();
    setResult(null);
    setState("idle");
    setStage(null);
    setStageMessage("");
    setError(null);
  }, []);

  const submit = useCallback(
    async (query: string, useStream = true) => {
      cancelRef.current?.();
      setState(useStream ? "streaming" : "loading");
      setStage(null);
      setStageMessage("");
      setError(null);
      setResult(null);

      if (useStream) {
        cancelRef.current = streamQuery(query, sessionId, {
          onStatus: (ev) => {
            setStage(ev.stage);
            setStageMessage(ev.message);
          },
          onResult: (r) => {
            setResult(r);
            setState("done");
            setSessionId(r.session_id);
          },
          onError: (msg) => {
            setError(msg);
            setState("error");
          },
          onDone: (sid) => {
            setSessionId(sid);
          },
        });
      } else {
        try {
          const r = await submitQuery(query, sessionId);
          setResult(r);
          setState("done");
          setSessionId(r.session_id);
        } catch (err) {
          setError(String(err));
          setState("error");
        }
      }
    },
    [sessionId]
  );

  return { result, state, stage, stageMessage, error, sessionId, submit, reset };
}
