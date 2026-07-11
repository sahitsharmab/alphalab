"use client";

/** Ticker input: the front door of the Investment Workspace. */

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { theme } from "@/lib/theme";

export default function TickerSearch({ autoFocus = false }: { autoFocus?: boolean }) {
  const router = useRouter();
  const [value, setValue] = useState("");

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const symbol = value.trim().toUpperCase();
    if (/^[A-Z0-9.\-^]{1,10}$/.test(symbol)) {
      router.push(`/workspace/${symbol}`);
    }
  };

  return (
    <form onSubmit={onSubmit} style={{ display: "flex", gap: 6 }}>
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ticker, e.g. MU"
        aria-label="Open investment workspace for ticker"
        autoFocus={autoFocus}
        style={{
          background: theme.surface,
          color: theme.inkPrimary,
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
          padding: "6px 10px",
          fontSize: 13,
          width: 130,
          outline: "none",
        }}
      />
      <button
        type="submit"
        style={{
          background: theme.surface,
          color: theme.inkSecondary,
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
          padding: "6px 12px",
          fontSize: 13,
          cursor: "pointer",
        }}
      >
        Open workspace
      </button>
    </form>
  );
}
