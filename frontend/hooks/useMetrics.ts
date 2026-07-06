"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchMetrics, fetchIngestionStats } from "@/lib/api";
import type { MetricsSummary, IngestionStats } from "@/types";

export function useMetrics(autoRefreshMs = 0) {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchMetrics();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    if (autoRefreshMs > 0) {
      const id = setInterval(refresh, autoRefreshMs);
      return () => clearInterval(id);
    }
  }, [refresh, autoRefreshMs]);

  return { metrics, loading, error, refresh };
}

export function useIngestionStats() {
  const [stats, setStats] = useState<IngestionStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchIngestionStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  return { stats, loading };
}
