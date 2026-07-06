"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchSessions, fetchSessionHistory } from "@/lib/api";
import type { Session, SessionHistory } from "@/types";

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchSessions(30);
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { sessions, loading, error, refresh };
}

export function useSessionHistory(sessionId: string | null) {
  const [history, setHistory] = useState<SessionHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) { setHistory(null); return; }
    setLoading(true);
    fetchSessionHistory(sessionId)
      .then((data) => { setHistory(data); setError(null); })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [sessionId]);

  return { history, loading, error };
}
