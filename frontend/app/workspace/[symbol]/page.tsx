"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import EvidenceSectionCard from "@/components/EvidenceSection";
import LineChart, { ChartPoint } from "@/components/LineChart";
import RiskPlanner from "@/components/RiskPlanner";
import TickerSearch from "@/components/TickerSearch";
import { getManualAnalysisPacket, getWorkspace, WorkspaceView } from "@/lib/api";
import { theme } from "@/lib/theme";

export default function WorkspacePage() {
  const params = useParams<{ symbol: string }>();
  const symbol = (params.symbol ?? "").toUpperCase();

  const [view, setView] = useState<WorkspaceView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copying" | "copied" | "error">(
    "idle",
  );

  const load = useCallback(
    async (refresh: boolean) => {
      setLoading(true);
      setError(null);
      try {
        setView(await getWorkspace(symbol, refresh));
      } catch (err: unknown) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    },
    [symbol],
  );

  useEffect(() => {
    if (symbol) void load(false);
  }, [symbol, load]);

  const pricePoints: ChartPoint[] = useMemo(
    () =>
      (view?.price_history ?? []).map((p) => ({
        date: new Date(p.date),
        value: p.close,
      })),
    [view],
  );

  const change = view?.quote.change_1d ?? null;

  const copyAnalysisPacket = useCallback(async () => {
    setCopyStatus("copying");
    try {
      const packet = await getManualAnalysisPacket(symbol);
      await navigator.clipboard.writeText(packet.content);
      setCopyStatus("copied");
      window.setTimeout(() => setCopyStatus("idle"), 2500);
    } catch {
      setCopyStatus("error");
    }
  }, [symbol]);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "2.5rem 1.5rem" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <Link href="/" style={{ color: theme.inkMuted, textDecoration: "none", fontSize: 13 }}>
            ← AlphaLab
          </Link>
          <h1 style={{ fontSize: "1.4rem", margin: 0 }}>
            {symbol}
            <span style={{ color: theme.inkMuted, fontWeight: 400, fontSize: "0.95rem" }}>
              {view ? ` · ${view.name}` : ""}
            </span>
          </h1>
        </div>
        <TickerSearch />
      </header>

      {view && (
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 12 }}>
          <span style={{ fontSize: 30, fontWeight: 600 }}>
            {view.quote.price.toLocaleString("en-US", { maximumFractionDigits: 2 })}
            <span style={{ fontSize: 13, color: theme.inkMuted, marginLeft: 6 }}>
              {view.currency}
            </span>
          </span>
          {change !== null && (
            <span
              style={{
                fontSize: 14,
                color: change >= 0 ? theme.deltaGood : theme.deltaBad,
              }}
            >
              {change >= 0 ? "▲" : "▼"} {(Math.abs(change) * 100).toFixed(2)}% (1d)
            </span>
          )}
          <span style={{ fontSize: 12, color: theme.inkMuted }}>
            {view.exchange} · as of {view.quote.price_date}
          </span>
          <button
            onClick={() => void copyAnalysisPacket()}
            disabled={copyStatus === "copying"}
            title="Copy the structured workspace and source links for analysis in ChatGPT or Claude"
            style={{
              marginLeft: "auto",
              background: theme.surface,
              color: copyStatus === "error" ? theme.statusCritical : theme.inkSecondary,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              padding: "5px 11px",
              fontSize: 12,
              cursor: copyStatus === "copying" ? "wait" : "pointer",
            }}
          >
            {copyStatus === "copying"
              ? "Preparing…"
              : copyStatus === "copied"
                ? "Copied research packet"
                : copyStatus === "error"
                  ? "Copy failed — retry"
                  : "Copy for ChatGPT / Claude"}
          </button>
          <button
            onClick={() => void load(true)}
            disabled={loading}
            style={{
              background: theme.surface,
              color: theme.inkSecondary,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              padding: "5px 11px",
              fontSize: 12,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? "Refreshing…" : "Refresh data"}
          </button>
        </div>
      )}

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
          ⚠ {error.includes("404") ? `Unknown symbol: ${symbol}` : `Backend error — ${error}`}
        </div>
      )}

      {!view && loading && (
        <p style={{ color: theme.inkMuted, marginTop: 32 }}>
          Building workspace for {symbol} — fetching price history…
        </p>
      )}

      {view && (
        <div style={{ display: "grid", gap: 16, marginTop: 20, opacity: loading ? 0.55 : 1 }}>
          <section
            style={{
              background: theme.surface,
              border: `1px solid ${theme.border}`,
              borderRadius: 12,
              padding: 16,
            }}
          >
            <h2 style={{ fontSize: 14, margin: "0 0 12px", color: theme.inkPrimary }}>
              Price — 1 year (adjusted)
            </h2>
            <LineChart
              points={pricePoints}
              color={theme.seriesYoy}
              format={(v) => v.toLocaleString("en-US", { maximumFractionDigits: 2 })}
              ariaLabel={`${symbol} adjusted close, one year`}
            />
          </section>

          {view.sections.map((section) => (
            <EvidenceSectionCard key={section.id} section={section} />
          ))}

          <RiskPlanner symbol={symbol} currentPrice={view.quote.price} />

          <p style={{ fontSize: 11, color: theme.inkMuted, margin: "4px 4px 0" }}>
            Generated {new Date(view.generated_at).toLocaleString("en-US")} · every statement is
            expandable to its evidence · AlphaLab informs your thinking; the decision is yours.
          </p>
          <p style={{ fontSize: 10, color: theme.inkMuted, margin: "0 4px" }}>
            This product uses the FRED® API but is not endorsed or certified by the Federal
            Reserve Bank of St. Louis.
          </p>
        </div>
      )}
    </main>
  );
}
