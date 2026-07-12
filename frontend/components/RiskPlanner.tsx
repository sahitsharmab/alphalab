"use client";

import { FormEvent, useEffect, useState } from "react";
import { createRiskPlan, RiskPlanAssessment } from "@/lib/api";
import { theme } from "@/lib/theme";

interface Props {
  symbol: string;
  currentPrice: number;
}

const fieldStyle = {
  background: theme.page,
  color: theme.inkPrimary,
  border: `1px solid ${theme.border}`,
  borderRadius: 7,
  padding: "7px 9px",
  width: "100%",
  boxSizing: "border-box" as const,
};

export default function RiskPlanner({ symbol, currentPrice }: Props) {
  const [entry, setEntry] = useState(currentPrice.toFixed(2));
  const [invalidation, setInvalidation] = useState("");
  const [target, setTarget] = useState("");
  const [accountSize, setAccountSize] = useState("");
  const [maxRisk, setMaxRisk] = useState("");
  const [result, setResult] = useState<RiskPlanAssessment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => setEntry(currentPrice.toFixed(2)), [currentPrice]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResult(
        await createRiskPlan({
          symbol,
          account_size: accountSize,
          entry,
          invalidation,
          target,
          max_dollar_risk: maxRisk,
        }),
      );
    } catch (caught: unknown) {
      setError(String(caught));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      style={{
        background: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        padding: 16,
      }}
    >
      <h2 style={{ fontSize: 14, margin: "0 0 5px", color: theme.inkPrimary }}>
        Risk Planner
      </h2>
      <p style={{ color: theme.inkMuted, fontSize: 11, margin: "0 0 14px" }}>
        You define the thesis invalidation. AlphaLab sizes the maximum position under your risk
        budget and tests it against daily volatility; it does not choose a stop or recommend a
        trade.
      </p>
      <form
        onSubmit={(event) => void submit(event)}
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(135px, 1fr))", gap: 10 }}
      >
        {[
          ["Account size ($)", accountSize, setAccountSize],
          ["Entry", entry, setEntry],
          ["Invalidation", invalidation, setInvalidation],
          ["Target", target, setTarget],
          ["Max dollar risk", maxRisk, setMaxRisk],
        ].map(([label, value, setter]) => (
          <label key={label as string} style={{ color: theme.inkSecondary, fontSize: 11 }}>
            {label as string}
            <input
              required
              min="0.01"
              step="0.01"
              type="number"
              value={value as string}
              onChange={(event) => (setter as (value: string) => void)(event.target.value)}
              style={{ ...fieldStyle, marginTop: 4 }}
            />
          </label>
        ))}
        <button
          type="submit"
          disabled={loading}
          style={{
            alignSelf: "end",
            background: theme.seriesYoy,
            color: theme.inkPrimary,
            border: 0,
            borderRadius: 7,
            padding: "8px 10px",
            cursor: loading ? "wait" : "pointer",
          }}
        >
          {loading ? "Calculating…" : "Calculate plan"}
        </button>
      </form>
      {error && <p role="alert" style={{ color: theme.statusCritical, fontSize: 12 }}>{error}</p>}
      {result && (
        <div style={{ marginTop: 16, borderTop: `1px solid ${theme.border}`, paddingTop: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(135px, 1fr))", gap: 10 }}>
            <Metric label="Direction" value={result.direction.toUpperCase()} />
            <Metric label="Risk / share" value={`$${number(result.dollar_risk_per_share)}`} />
            <Metric label="Maximum shares" value={result.maximum_shares.toLocaleString("en-US")} />
            <Metric label="Position value" value={`$${number(result.position_value)}`} />
            <Metric label="Account exposure" value={`${number(result.account_exposure_pct)}%`} />
            <Metric label="Account at risk" value={`${number(result.account_risk_pct)}%`} />
            <Metric label="Risk / reward" value={`1 : ${number(result.risk_reward_ratio)}`} />
            <Metric
              label="Invalidation distance"
              value={result.invalidation_distance_atr ? `${number(result.invalidation_distance_atr)} ATR` : "Unavailable"}
            />
          </div>
          {result.warnings.map((warning) => (
            <p key={warning} style={{ color: theme.inkSecondary, fontSize: 12, margin: "10px 0 0" }}>
              ⚠ {warning}
            </p>
          ))}
          <p style={{ color: theme.inkMuted, fontSize: 10, margin: "10px 0 0" }}>
            {result.assumptions.join(" ")}
          </p>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ color: theme.inkMuted, fontSize: 10 }}>{label}</div>
      <div style={{ color: theme.inkPrimary, fontSize: 14, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function number(value: string): string {
  return Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 });
}
