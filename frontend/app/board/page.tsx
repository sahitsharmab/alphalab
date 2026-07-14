"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { BoardLevel, DecisionBoard, DecisionBoardRow, getDecisionBoard } from "@/lib/api";
import { theme } from "@/lib/theme";

const ROLE_COLOR: Record<string, string> = {
  Hedge: theme.seriesYoy,
  Defensive: theme.seriesIndex,
  Core: theme.inkSecondary,
  "High-beta": "#d99a2b",
  "Very high-beta": theme.deltaBad,
  Unclassified: theme.inkMuted,
};

export default function BoardPage() {
  const [board, setBoard] = useState<DecisionBoard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setBoard(await getDecisionBoard());
      setError(null);
    } catch (caught: unknown) {
      setError(String(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void load(), [load]);

  const rows = board?.rows ?? [];

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: "2.5rem 1.5rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ display: "flex", gap: 14, alignItems: "baseline" }}>
            <Link href="/" style={{ color: theme.inkMuted, textDecoration: "none", fontSize: 12 }}>
              ← AlphaLab
            </Link>
            <Link href="/watchlist" style={{ color: theme.inkMuted, textDecoration: "none", fontSize: 12 }}>
              Watchlist
            </Link>
          </div>
          <h1 style={{ margin: "6px 0 0", fontSize: "1.5rem" }}>Decision Board</h1>
          <p style={{ color: theme.inkMuted, fontSize: 12, margin: "4px 0 0" }}>
            Role by beta · support/resistance from the EMA ladder · deterministic facts only —
            which level fires is your call.
          </p>
        </div>
        <button onClick={() => void load()} disabled={loading} style={refreshStyle}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </header>

      {board?.next_catalyst && (
        <div style={catalystStyle}>
          <span style={{ color: theme.inkMuted, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Next market catalyst
          </span>
          <span style={{ color: theme.inkPrimary, fontSize: 14, fontWeight: 600 }}>{board.next_catalyst}</span>
        </div>
      )}

      {error && <p role="alert" style={{ color: theme.statusCritical, fontSize: 12, marginTop: 16 }}>{error}</p>}

      {loading && !board ? (
        <p style={{ color: theme.inkMuted, marginTop: 24 }}>Loading board…</p>
      ) : rows.length === 0 ? (
        <p style={{ color: theme.inkMuted, fontSize: 13, marginTop: 24 }}>
          No symbols on the watchlist yet. Add tickers from the{" "}
          <Link href="/watchlist" style={{ color: theme.seriesYoy }}>watchlist</Link> to populate the board.
        </p>
      ) : (
        <div style={{ overflowX: "auto", border: `1px solid ${theme.border}`, borderRadius: 12, marginTop: 18 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontVariantNumeric: "tabular-nums" }}>
            <thead>
              <tr style={{ color: theme.inkMuted, textAlign: "right" }}>
                {["Symbol", "Role", "Price", "β", "1D", "1W", "1M", "vs SPY", "Support", "Resistance", "Plan"].map(
                  (h, i) => (
                    <th key={h} style={{ padding: "10px 10px", textAlign: i < 2 ? "left" : "right", fontWeight: 500 }}>
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <Row key={row.symbol} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ color: theme.inkMuted, fontSize: 10, marginTop: 12, lineHeight: 1.5 }}>
        Role is the name&apos;s 1-year beta vs SPY, banded. Support/resistance are the nearest EMAs
        below/above the last close — the levels, not a signal. Each row uses that name&apos;s own latest
        stored daily bar (its date shows on the ticker&apos;s workspace), so names refreshed at different
        times can differ by a session. Scenario reasoning — which name fits which outcome — is the AI
        layer, not shown here.
      </p>
    </main>
  );
}

function Row({ row }: { row: DecisionBoardRow }) {
  return (
    <tr style={{ borderTop: `1px solid ${theme.border}`, textAlign: "right" }}>
      <td style={{ padding: "11px 10px", textAlign: "left" }}>
        <Link href={`/workspace/${row.symbol}`} style={{ color: theme.inkPrimary, textDecoration: "none" }}>
          <strong>{row.symbol}</strong>
        </Link>
        <div style={{ color: theme.inkMuted, fontSize: 10, maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {row.name}
        </div>
      </td>
      <td style={{ padding: "11px 10px", textAlign: "left" }}>
        <span style={{
          display: "inline-block", padding: "2px 8px", borderRadius: 999, fontSize: 10.5,
          color: ROLE_COLOR[row.role] ?? theme.inkSecondary,
          border: `1px solid ${ROLE_COLOR[row.role] ?? theme.border}44`,
          background: `${ROLE_COLOR[row.role] ?? theme.inkMuted}14`, whiteSpace: "nowrap",
        }}>
          {row.role}
        </span>
      </td>
      <td style={{ padding: "11px 10px", color: theme.inkPrimary }}>{row.price.toFixed(2)}</td>
      <td style={{ padding: "11px 10px", color: theme.inkSecondary }}>{row.beta === null ? "—" : row.beta.toFixed(2)}</td>
      {[row.change_1d, row.return_1w, row.return_1m, row.relative_1m_spy].map((v, i) => (
        <td key={i} style={{ padding: "11px 10px", color: color(v) }}>{pct(v)}</td>
      ))}
      <td style={{ padding: "11px 10px" }}><Level level={row.support} /></td>
      <td style={{ padding: "11px 10px" }}><Level level={row.resistance} /></td>
      <td style={{ padding: "11px 10px", color: row.has_risk_plan ? theme.seriesIndex : theme.inkMuted }}>
        {row.has_risk_plan ? "✓" : "—"}
      </td>
    </tr>
  );
}

function Level({ level }: { level: BoardLevel | null }) {
  if (!level) return <span style={{ color: theme.inkMuted }}>—</span>;
  return (
    <span style={{ whiteSpace: "nowrap" }}>
      <span style={{ color: theme.inkPrimary }}>{level.value.toFixed(2)}</span>
      <span style={{ color: theme.inkMuted, fontSize: 10 }}>
        {" "}{level.label} · {pct(level.distance)}
      </span>
    </span>
  );
}

const refreshStyle = {
  background: theme.surface,
  color: theme.inkSecondary,
  border: `1px solid ${theme.border}`,
  borderRadius: 8,
  padding: "6px 12px",
  fontSize: 12,
  cursor: "pointer",
};
const catalystStyle = {
  display: "flex",
  gap: 12,
  alignItems: "baseline",
  flexWrap: "wrap" as const,
  marginTop: 16,
  padding: "10px 14px",
  background: theme.surface,
  border: `1px solid ${theme.border}`,
  borderLeft: `3px solid ${theme.seriesYoy}`,
  borderRadius: 10,
};

function pct(value: number | null): string {
  return value === null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

function color(value: number | null): string {
  if (value === null) return theme.inkMuted;
  return value >= 0 ? theme.deltaGood : theme.deltaBad;
}
