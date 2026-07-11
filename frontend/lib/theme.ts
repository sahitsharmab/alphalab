/** Dark-mode chart tokens (validated palette — see DECISIONS.md Session 004). */

export const theme = {
  page: "#0d0d0d",
  surface: "#1a1a19",
  inkPrimary: "#ffffff",
  inkSecondary: "#c3c2b7",
  inkMuted: "#898781",
  grid: "#2c2c2a",
  baseline: "#383835",
  border: "rgba(255,255,255,0.10)",
  // Series colors, validated against the dark surface (CVD ΔE 69.8, ≥3:1).
  seriesYoy: "#3987e5",
  seriesIndex: "#199e70",
  // Delta colors: direction × whether up is good (rising inflation = bad).
  deltaGood: "#0ca30c",
  deltaBad: "#d03b3b",
  statusOk: "#0ca30c",
  statusCritical: "#d03b3b",
} as const;
