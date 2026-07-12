"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import LineChart, { ChartPoint } from "@/components/LineChart";
import StatTile from "@/components/StatTile";
import TickerSearch from "@/components/TickerSearch";
import {
  getHealth,
  getObservations,
  ingestNowflation,
  Health,
  Observation,
  SERIES,
} from "@/lib/api";
import { theme } from "@/lib/theme";

type RangeKey = "90d" | "1y" | "5y" | "all";

const RANGES: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "90d", label: "90D", days: 90 },
  { key: "1y", label: "1Y", days: 365 },
  { key: "5y", label: "5Y", days: 1826 },
  { key: "all", label: "All", days: null },
];

const formatPercent = (v: number) => `${(v * 100).toFixed(2)}%`;
const formatIndex = (v: number) => v.toFixed(1);

function toPoints(observations: Observation[]): ChartPoint[] {
  return observations.map((o) => ({
    date: new Date(o.observation_date),
    value: Number(o.value),
  }));
}

/** Delta of the last value vs the value ~`days` days earlier. */
function deltaOver(points: ChartPoint[], days: number): number | null {
  if (points.length < 2) return null;
  const last = points[points.length - 1];
  const target = last.date.getTime() - days * 86_400_000;
  let previous = points[0];
  for (const p of points) {
    if (p.date.getTime() <= target) previous = p;
    else break;
  }
  return last.value - previous.value;
}

function startFor(range: RangeKey): string | undefined {
  const preset = RANGES.find((r) => r.key === range);
  if (!preset?.days) return undefined;
  const d = new Date(Date.now() - preset.days * 86_400_000);
  return d.toISOString().slice(0, 10);
}

function DataTable({
  points,
  format,
}: {
  points: ChartPoint[];
  format: (v: number) => string;
}) {
  return (
    <details style={{ marginTop: 10 }}>
      <summary style={{ fontSize: 12, color: theme.inkMuted, cursor: "pointer" }}>
        View data ({points.length} rows)
      </summary>
      <div style={{ maxHeight: 240, overflowY: "auto", marginTop: 8 }}>
        <table
          style={{
            width: "100%",
            fontSize: 12,
            color: theme.inkSecondary,
            borderCollapse: "collapse",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <thead>
            <tr style={{ color: theme.inkMuted, textAlign: "left" }}>
              <th style={{ padding: "4px 8px" }}>Date</th>
              <th style={{ padding: "4px 8px", textAlign: "right" }}>Value</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.date.toISOString()}>
                <td style={{ padding: "2px 8px" }}>
                  {p.date.toISOString().slice(0, 10)}
                </td>
                <td style={{ padding: "2px 8px", textAlign: "right" }}>
                  {format(p.value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function ChartCard({
  title,
  subtitle,
  points,
  color,
  format,
  loading,
}: {
  title: string;
  subtitle: string;
  points: ChartPoint[];
  color: string;
  format: (v: number) => string;
  loading: boolean;
}) {
  return (
    <section
      style={{
        background: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        padding: 16,
      }}
    >
      <h2 style={{ fontSize: 14, margin: 0, color: theme.inkPrimary }}>{title}</h2>
      <p style={{ fontSize: 12, margin: "2px 0 12px", color: theme.inkMuted }}>
        {subtitle}
      </p>
      <div style={{ opacity: loading ? 0.55 : 1, transition: "opacity 120ms" }}>
        <LineChart points={points} color={color} format={format} ariaLabel={title} />
      </div>
      <DataTable points={points} format={format} />
    </section>
  );
}

export default function DashboardPage() {
  const [range, setRange] = useState<RangeKey>("1y");
  const [yoy, setYoy] = useState<Observation[]>([]);
  const [index, setIndex] = useState<Observation[]>([]);
  const [coverage, setCoverage] = useState<Observation[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (activeRange: RangeKey) => {
    setLoading(true);
    setError(null);
    try {
      const start = startFor(activeRange);
      const coverageStart = new Date(Date.now() - 40 * 86_400_000)
        .toISOString()
        .slice(0, 10);
      const [yoyData, indexData, coverageData] = await Promise.all([
        getObservations(SERIES.yoy, start),
        getObservations(SERIES.index, start),
        getObservations(SERIES.coverage, coverageStart),
      ]);
      setYoy(yoyData);
      setIndex(indexData);
      setCoverage(coverageData);
    } catch (err: unknown) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(range);
  }, [load, range]);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const onUpdate = async () => {
    setUpdating(true);
    setError(null);
    try {
      await ingestNowflation();
      await load(range);
    } catch (err: unknown) {
      setError(String(err));
    } finally {
      setUpdating(false);
    }
  };

  const yoyPoints = useMemo(() => toPoints(yoy), [yoy]);
  const indexPoints = useMemo(() => toPoints(index), [index]);

  const lastYoy = yoyPoints.at(-1);
  const lastIndex = indexPoints.at(-1);
  const lastCoverage = coverage.at(-1);
  const yoyDelta = deltaOver(yoyPoints, 30);
  const indexDelta = deltaOver(indexPoints, 30);
  const lastUpdated = yoy.at(-1)?.as_of;

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "2.5rem 1.5rem" }}>
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.6rem", margin: 0 }}>AlphaLab</h1>
          <p style={{ color: theme.inkMuted, margin: "2px 0 0", fontSize: 13 }}>
            Macro intelligence — Nowflation daily inflation gauge
          </p>
        </div>
        <TickerSearch autoFocus />
        <Link href="/watchlist" style={{ color: theme.inkSecondary, fontSize: 12 }}>
          Open watchlist
        </Link>
        {health && (
          <span style={{ fontSize: 12, color: theme.inkMuted }}>
            <span
              style={{
                color: health.status === "ok" ? theme.statusOk : theme.statusCritical,
                marginRight: 6,
              }}
            >
              ●
            </span>
            {health.status === "ok" ? "All systems healthy" : "Degraded"} · v
            {health.version}
          </span>
        )}
      </header>

      {error && (
        <div
          role="alert"
          style={{
            marginTop: 16,
            padding: "10px 14px",
            borderRadius: 8,
            border: `1px solid ${theme.statusCritical}`,
            color: theme.inkSecondary,
            fontSize: 13,
          }}
        >
          ⚠ Backend error — {error}
        </div>
      )}

      {/* KPI row */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 20 }}>
        <StatTile
          label="Inflation, year over year"
          value={lastYoy ? formatPercent(lastYoy.value) : "—"}
          delta={
            yoyDelta !== null
              ? {
                  text: `${Math.abs(yoyDelta * 100).toFixed(2)} pp vs 30d ago`,
                  direction: yoyDelta > 0 ? "up" : yoyDelta < 0 ? "down" : "flat",
                  upIsGood: false,
                }
              : undefined
          }
        />
        <StatTile
          label="Headline gauge index"
          value={lastIndex ? formatIndex(lastIndex.value) : "—"}
          delta={
            indexDelta !== null
              ? {
                  text: `${Math.abs(indexDelta).toFixed(2)} vs 30d ago`,
                  direction: indexDelta > 0 ? "up" : indexDelta < 0 ? "down" : "flat",
                  upIsGood: false,
                }
              : undefined
          }
        />
        <StatTile
          label="Basket coverage"
          value={lastCoverage ? `${(Number(lastCoverage.value) * 100).toFixed(0)}%` : "—"}
        />
      </div>

      {/* Filter row: date range presets + refresh */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
          margin: "20px 0 12px",
        }}
      >
        <div role="group" aria-label="Date range" style={{ display: "flex", gap: 6 }}>
          {RANGES.map((preset) => {
            const selected = preset.key === range;
            return (
              <button
                key={preset.key}
                onClick={() => setRange(preset.key)}
                aria-pressed={selected}
                style={{
                  background: selected ? theme.surface : "transparent",
                  color: selected ? theme.inkPrimary : theme.inkMuted,
                  border: `1px solid ${selected ? theme.border : "transparent"}`,
                  borderRadius: 8,
                  padding: "6px 12px",
                  fontSize: 13,
                  fontWeight: selected ? 600 : 400,
                  cursor: "pointer",
                }}
              >
                {selected ? "✓ " : ""}
                {preset.label}
              </button>
            );
          })}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {lastUpdated && (
            <span style={{ fontSize: 12, color: theme.inkMuted }}>
              Data as of{" "}
              {new Date(lastUpdated).toLocaleString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
          )}
          <button
            onClick={onUpdate}
            disabled={updating}
            style={{
              background: theme.surface,
              color: theme.inkSecondary,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: 13,
              cursor: updating ? "wait" : "pointer",
            }}
          >
            {updating ? "Updating…" : "Update data"}
          </button>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: "grid", gap: 16 }}>
        <ChartCard
          title="Inflation, year over year"
          subtitle="Nowflation headline gauge, daily · fraction shown as percent"
          points={yoyPoints}
          color={theme.seriesYoy}
          format={formatPercent}
          loading={loading}
        />
        <ChartCard
          title="Headline gauge index"
          subtitle="Market-price inflation index · January 2018 = 100"
          points={indexPoints}
          color={theme.seriesIndex}
          format={formatIndex}
          loading={loading}
        />
      </div>
    </main>
  );
}
