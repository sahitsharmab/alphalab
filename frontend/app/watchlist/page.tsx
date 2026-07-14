"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  addWatchlistItem,
  getWatchlistOverview,
  removeWatchlistItem,
  WatchlistOverviewRow,
} from "@/lib/api";
import { theme } from "@/lib/theme";

export default function WatchlistPage() {
  const [rows, setRows] = useState<WatchlistOverviewRow[]>([]);
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await getWatchlistOverview());
      setError(null);
    } catch (caught: unknown) {
      setError(String(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => void load(), [load]);

  async function add(event: FormEvent) {
    event.preventDefault();
    try {
      await addWatchlistItem(symbol.trim().toUpperCase(), note.trim());
      setSymbol("");
      setNote("");
      await load();
    } catch (caught: unknown) {
      setError(String(caught));
    }
  }

  async function remove(symbolToRemove: string) {
    await removeWatchlistItem(symbolToRemove);
    await load();
  }

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "2.5rem 1.5rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div style={{ display: "flex", gap: 14, alignItems: "baseline" }}>
            <Link href="/" style={{ color: theme.inkMuted, textDecoration: "none", fontSize: 12 }}>
              ← AlphaLab
            </Link>
            <Link href="/board" style={{ color: theme.seriesYoy, textDecoration: "none", fontSize: 12 }}>
              Decision Board →
            </Link>
          </div>
          <h1 style={{ margin: "6px 0 0", fontSize: "1.5rem" }}>Momentum Watchlist</h1>
          <p style={{ color: theme.inkMuted, fontSize: 12, margin: "4px 0 0" }}>
            User-selected symbols only · deterministic daily context · no opaque ranking score
          </p>
        </div>
      </header>

      <form
        onSubmit={(event) => void add(event)}
        style={{ display: "flex", flexWrap: "wrap", gap: 8, margin: "20px 0" }}
      >
        <input
          required
          value={symbol}
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="Ticker"
          aria-label="Ticker to add"
          style={inputStyle}
        />
        <input
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Optional thesis note"
          aria-label="Watchlist note"
          style={{ ...inputStyle, minWidth: 240 }}
        />
        <button type="submit" style={buttonStyle}>Add symbol</button>
      </form>

      {error && <p role="alert" style={{ color: theme.statusCritical, fontSize: 12 }}>{error}</p>}
      {loading ? (
        <p style={{ color: theme.inkMuted }}>Loading watchlist…</p>
      ) : rows.length === 0 ? (
        <p style={{ color: theme.inkMuted, fontSize: 13 }}>
          No symbols yet. Build a ticker workspace first, then add it here.
        </p>
      ) : (
        <div style={{ overflowX: "auto", border: `1px solid ${theme.border}`, borderRadius: 12 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ color: theme.inkMuted, textAlign: "right" }}>
                {[
                  "Symbol", "Price", "1D", "1W", "1M", "vs EMA9", "vs EMA21",
                  "1M vs SPY", "1M vs QQQ", "Note", "",
                ].map((heading) => <th key={heading} style={{ padding: "10px 8px" }}>{heading}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.symbol} style={{ borderTop: `1px solid ${theme.border}`, textAlign: "right" }}>
                  <td style={{ padding: "10px 8px", textAlign: "left" }}>
                    <Link href={`/workspace/${row.symbol}`} style={{ color: theme.inkPrimary }}>
                      <strong>{row.symbol}</strong>
                    </Link>
                    <div style={{ color: theme.inkMuted, fontSize: 10 }}>{row.name}</div>
                  </td>
                  <td style={{ padding: "10px 8px" }}>{row.price.toFixed(2)}</td>
                  {[row.change_1d, row.return_1w, row.return_1m, row.ema9_distance,
                    row.ema21_distance, row.relative_1m_spy, row.relative_1m_qqq].map((value, index) => (
                    <td key={index} style={{ padding: "10px 8px", color: color(value) }}>{pct(value)}</td>
                  ))}
                  <td style={{ padding: "10px 8px", color: theme.inkSecondary }}>{row.note || "—"}</td>
                  <td style={{ padding: "10px 8px" }}>
                    <button onClick={() => void remove(row.symbol)} style={smallButtonStyle}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ color: theme.inkMuted, fontSize: 10, marginTop: 10 }}>
        SPY and QQQ are ETF proxies. Positive relative return means the stock outperformed over the
        same shared trading dates. Values use the latest stored daily bars.
      </p>
    </main>
  );
}

const inputStyle = {
  background: theme.surface,
  color: theme.inkPrimary,
  border: `1px solid ${theme.border}`,
  borderRadius: 8,
  padding: "7px 10px",
};
const buttonStyle = { ...inputStyle, cursor: "pointer", color: theme.inkSecondary };
const smallButtonStyle = { ...buttonStyle, padding: "4px 7px", fontSize: 10 };

function pct(value: number | null): string {
  return value === null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

function color(value: number | null): string {
  if (value === null) return theme.inkMuted;
  return value >= 0 ? theme.deltaGood : theme.deltaBad;
}
