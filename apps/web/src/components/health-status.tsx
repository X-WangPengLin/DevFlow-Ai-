"use client";

import { useEffect, useState } from "react";

type Health = "checking" | "online" | "offline";

export function HealthStatus() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    const controller = new AbortController();
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    fetch(`${baseUrl}/health`, { signal: controller.signal, cache: "no-store" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("HTTP error")))
      .then((data: { status?: string }) => setHealth(data.status === "ok" ? "online" : "offline"))
      .catch((error: unknown) => { if ((error as Error).name !== "AbortError") setHealth("offline"); });
    return () => controller.abort();
  }, []);

  const label = { checking: "检查中", online: "后端在线", offline: "后端离线" }[health];
  return <span className={`health health-${health}`} role="status"><span className="health-dot" />{label}</span>;
}
