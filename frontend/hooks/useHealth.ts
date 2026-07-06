"use client";

import { useState, useEffect } from "react";
import { fetchHealth } from "@/lib/api";

export type HealthStatus = "checking" | "online" | "offline";

export function useHealth(intervalMs = 30000) {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let active = true;

    async function check() {
      try {
        const r = await fetchHealth();
        if (active) setStatus(r.status === "ok" ? "online" : "offline");
      } catch {
        if (active) setStatus("offline");
      }
    }

    check();
    const id = setInterval(check, intervalMs);
    return () => { active = false; clearInterval(id); };
  }, [intervalMs]);

  return status;
}
