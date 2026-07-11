"use client";

/** Stat tile: label · value · optional delta (direction × whether up is good). */

import { theme } from "@/lib/theme";

interface Props {
  label: string;
  value: string;
  delta?: {
    text: string;
    direction: "up" | "down" | "flat";
    upIsGood: boolean;
  };
}

export default function StatTile({ label, value, delta }: Props) {
  let deltaColor: string = theme.inkMuted;
  if (delta && delta.direction !== "flat") {
    const isGood = (delta.direction === "up") === delta.upIsGood;
    deltaColor = isGood ? theme.deltaGood : theme.deltaBad;
  }
  return (
    <div
      style={{
        background: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: 12,
        padding: "14px 16px",
        minWidth: 150,
        flex: "1 1 150px",
      }}
    >
      <div style={{ fontSize: 12, color: theme.inkMuted }}>{label}</div>
      <div
        style={{
          fontSize: 26,
          fontWeight: 600,
          color: theme.inkPrimary,
          marginTop: 4,
        }}
      >
        {value}
      </div>
      {delta && (
        <div style={{ fontSize: 12, color: deltaColor, marginTop: 4 }}>
          {delta.direction === "up" ? "▲" : delta.direction === "down" ? "▼" : "—"}{" "}
          {delta.text}
        </div>
      )}
    </div>
  );
}
