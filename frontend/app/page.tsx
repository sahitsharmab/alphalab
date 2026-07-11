"use client";

import { useEffect, useState } from "react";

interface DatabaseHealth {
  status: "ok" | "unavailable";
  latency_ms: number | null;
  error: string | null;
}

interface Health {
  status: "ok" | "degraded";
  environment: string;
  version: string;
  database: DatabaseHealth;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/health`)
      .then((response) => response.json() as Promise<Health>)
      .then(setHealth)
      .catch((err: unknown) => setError(String(err)));
  }, []);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "4rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem" }}>AlphaLab</h1>
      <p style={{ color: "#8a93a5", marginTop: 0 }}>
        Financial Intelligence Platform
      </p>

      <section
        style={{
          marginTop: "2rem",
          padding: "1.5rem",
          borderRadius: 12,
          border: "1px solid #1e2633",
          background: "#101623",
        }}
      >
        <h2 style={{ fontSize: "1rem", marginTop: 0 }}>Platform Health</h2>

        {!health && !error && <p>Checking…</p>}

        {error && (
          <p style={{ color: "#f2708a" }}>Backend unreachable: {error}</p>
        )}

        {health && (
          <dl style={{ display: "grid", gridTemplateColumns: "10rem 1fr", rowGap: "0.5rem", margin: 0 }}>
            <dt style={{ color: "#8a93a5" }}>Status</dt>
            <dd style={{ margin: 0, color: health.status === "ok" ? "#5ad19a" : "#f5b45f" }}>
              {health.status}
            </dd>
            <dt style={{ color: "#8a93a5" }}>Environment</dt>
            <dd style={{ margin: 0 }}>{health.environment}</dd>
            <dt style={{ color: "#8a93a5" }}>Version</dt>
            <dd style={{ margin: 0 }}>{health.version}</dd>
            <dt style={{ color: "#8a93a5" }}>Database</dt>
            <dd style={{ margin: 0, color: health.database.status === "ok" ? "#5ad19a" : "#f2708a" }}>
              {health.database.status}
              {health.database.latency_ms !== null &&
                ` (${health.database.latency_ms} ms)`}
            </dd>
          </dl>
        )}
      </section>
    </main>
  );
}
