"""M1a live probe: Twelve Data regular-session behavior (run on a weekday).

Measures what the Sunday verification could not (M1A_PROVIDER_SCORECARD.md):

1. Arrival delay — how long after a minute closes does its bar appear?
2. Current-bar behavior — are in-progress bars served, and do they revise?
3. Completed-bar revisions — do finalized bars ever change afterwards?
4. NBIS native 5m vs deterministic aggregation of 1m (the unresolved mismatch).

Usage (start ~09:25 ET):

    cd backend
    python -m poetry run python scripts/m1a_probe.py --minutes 75

Budget: 3 x 1min fetches per cycle + 1 x 5min fetch every 5th cycle stays
within Twelve Data Basic's 8 credits/minute. Results land in
``scripts/m1a_results/`` (gitignored): ``events.jsonl`` + ``summary.json``.
The API key is read from ALPHALAB_TWELVE_DATA_API_KEY (env or root .env)
and never written to the output.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

BASE_URL = "https://api.twelvedata.com/time_series"
SYMBOLS = ("NBIS", "SPY", "QQQ")
ET = ZoneInfo("America/New_York")
CYCLE_SECONDS = 60
FIVE_MIN_EVERY = 5  # fetch NBIS native 5m every Nth cycle
OHLCV = ("open", "high", "low", "close", "volume")


def load_key() -> str:
    key = os.environ.get("ALPHALAB_TWELVE_DATA_API_KEY", "")
    if key:
        return key
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line:
                name, value = line.split("=", 1)
                if name.strip() == "ALPHALAB_TWELVE_DATA_API_KEY":
                    return value.strip()
    raise SystemExit("ALPHALAB_TWELVE_DATA_API_KEY not found (env or root .env)")


def now_et() -> datetime:
    return datetime.now(UTC).astimezone(ET)


def fetch_series(client: httpx.Client, key: str, symbol: str, interval: str) -> dict[str, Any]:
    response = client.get(
        BASE_URL,
        params={
            "symbol": symbol,
            "interval": interval,
            "outputsize": "12",
            "timezone": "America/New_York",
            "apikey": key,
        },
        timeout=15,
    )
    payload: dict[str, Any] = response.json()
    return payload


class Probe:
    def __init__(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = out_dir / "events.jsonl"
        self.summary_path = out_dir / "summary.json"
        # bars[symbol][bar_open "YYYY-MM-DD HH:MM:SS"] tracking dict
        self.bars: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in SYMBOLS}
        self.native_5m: dict[str, dict[str, str]] = {}
        self.appearance_lags: dict[str, list[float]] = {s: [] for s in SYMBOLS}
        self.revision_events: list[dict[str, Any]] = []
        self.partial_bar_polls: dict[str, int] = dict.fromkeys(SYMBOLS, 0)
        self.polls: dict[str, int] = dict.fromkeys(SYMBOLS, 0)
        self.errors: list[dict[str, Any]] = []
        self.five_min_diffs: list[dict[str, Any]] = []

    def log(self, event: dict[str, Any]) -> None:
        event["t"] = now_et().isoformat()
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")

    def record_poll(self, symbol: str, payload: dict[str, Any]) -> None:
        wall = now_et()
        values = payload.get("values")
        if payload.get("status") == "error" or not isinstance(values, list):
            self.errors.append(
                {"symbol": symbol, "payload": {k: payload.get(k) for k in ("code", "message")}}
            )
            self.log(
                {
                    "type": "error",
                    "symbol": symbol,
                    "code": payload.get("code"),
                    "message": payload.get("message"),
                }
            )
            return
        self.polls[symbol] += 1
        newest = values[0]  # Twelve Data returns newest first
        newest_open = datetime.strptime(newest["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
        newest_close = newest_open.timestamp() + 60
        is_partial = wall.timestamp() < newest_close
        if is_partial:
            self.partial_bar_polls[symbol] += 1
        self.log(
            {
                "type": "poll",
                "symbol": symbol,
                "newest_bar": newest["datetime"],
                "newest_is_in_progress_minute": is_partial,
                "seconds_since_newest_bar_close": round(wall.timestamp() - newest_close, 1),
            }
        )
        for row in values:
            self._track_bar(symbol, row, wall)

    def _track_bar(self, symbol: str, row: dict[str, Any], wall: datetime) -> None:
        bar_open = row["datetime"]
        snapshot = {field: row.get(field) for field in OHLCV}
        known = self.bars[symbol].get(bar_open)
        if known is None:
            open_dt = datetime.strptime(bar_open, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
            lag = wall.timestamp() - (open_dt.timestamp() + 60)  # vs bar CLOSE
            self.bars[symbol][bar_open] = {
                "first_seen": wall.isoformat(),
                "values": snapshot,
                "revs": 0,
            }
            if 0 <= lag <= CYCLE_SECONDS * 2:  # freshly closed bar -> appearance lag sample
                self.appearance_lags[symbol].append(round(lag, 1))
                self.log(
                    {
                        "type": "appearance",
                        "symbol": symbol,
                        "bar": bar_open,
                        "lag_seconds": round(lag, 1),
                    }
                )
            return
        if known["values"] != snapshot:
            open_dt = datetime.strptime(bar_open, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
            was_final = wall.timestamp() > open_dt.timestamp() + 120  # changed well after close
            changed = {
                field: {"from": known["values"][field], "to": snapshot[field]}
                for field in OHLCV
                if known["values"][field] != snapshot[field]
            }
            known["values"] = snapshot
            known["revs"] += 1
            event = {
                "type": "revision",
                "symbol": symbol,
                "bar": bar_open,
                "bar_was_final": was_final,
                "changed": changed,
            }
            self.revision_events.append(event)
            self.log(event)

    def check_native_5m(self, payload: dict[str, Any]) -> None:
        values = payload.get("values")
        if payload.get("status") == "error" or not isinstance(values, list):
            return
        ones = self.bars["NBIS"]
        for row in values:
            start = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ET)
            components = []
            for offset in range(5):
                key = start.timestamp() + offset * 60
                stamp = datetime.fromtimestamp(key, tz=ET).strftime("%Y-%m-%d %H:%M:%S")
                bar = ones.get(stamp)
                if bar is None:
                    break
                components.append(bar["values"])
            if len(components) != 5:
                continue  # only judge fully covered windows
            derived = {
                "open": components[0]["open"],
                "high": f"{max(float(c['high']) for c in components):.5f}",
                "low": f"{min(float(c['low']) for c in components):.5f}",
                "close": components[-1]["close"],
                "volume": str(sum(int(float(c["volume"])) for c in components)),
            }
            mismatched = {
                field: {"native": row.get(field), "derived": derived[field]}
                for field in OHLCV
                if abs(float(row.get(field, 0)) - float(derived[field])) > 1e-4
            }
            if mismatched and row["datetime"] not in self.native_5m:
                event = {"type": "five_min_mismatch", "bar": row["datetime"], "fields": mismatched}
                self.five_min_diffs.append(event)
                self.log(event)
            self.native_5m[row["datetime"]] = row["datetime"]

    def summary(self) -> dict[str, Any]:
        def lag_stats(lags: list[float]) -> dict[str, float] | None:
            if not lags:
                return None
            return {
                "samples": len(lags),
                "min": min(lags),
                "median": round(statistics.median(lags), 1),
                "max": max(lags),
            }

        return {
            "generated_at": now_et().isoformat(),
            "per_symbol": {
                symbol: {
                    "polls": self.polls[symbol],
                    "bars_tracked": len(self.bars[symbol]),
                    "appearance_lag_seconds_after_bar_close": lag_stats(
                        self.appearance_lags[symbol]
                    ),
                    "polls_where_newest_bar_was_in_progress": self.partial_bar_polls[symbol],
                    "revisions": sum(1 for e in self.revision_events if e["symbol"] == symbol),
                    "revisions_to_final_bars": sum(
                        1
                        for e in self.revision_events
                        if e["symbol"] == symbol and e["bar_was_final"]
                    ),
                }
                for symbol in SYMBOLS
            },
            "nbis_5m_windows_checked": len(self.native_5m),
            "nbis_5m_mismatches": self.five_min_diffs,
            "errors": len(self.errors),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=75, help="how long to run")
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent / "m1a_results", help="output directory"
    )
    args = parser.parse_args()

    key = load_key()
    probe = Probe(args.out)
    start = now_et()
    if (start.hour, start.minute) < (9, 30):
        print(f"[{start:%H:%M:%S} ET] before the open — early polls show last-session bars")
    print(f"Running {args.minutes} cycles; results -> {args.out}")

    with httpx.Client() as client:
        for cycle in range(1, args.minutes + 1):
            cycle_started = time.monotonic()
            for symbol in SYMBOLS:
                try:
                    probe.record_poll(symbol, fetch_series(client, key, symbol, "1min"))
                except httpx.HTTPError as exc:
                    probe.log({"type": "transport_error", "symbol": symbol, "error": str(exc)})
            if cycle % FIVE_MIN_EVERY == 0:
                try:
                    probe.check_native_5m(fetch_series(client, key, "NBIS", "5min"))
                except httpx.HTTPError as exc:
                    probe.log({"type": "transport_error", "symbol": "NBIS/5min", "error": str(exc)})
            summary = probe.summary()
            probe.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            if cycle % 5 == 0 or cycle == 1:
                lags = summary["per_symbol"]["SPY"]["appearance_lag_seconds_after_bar_close"]
                print(
                    f"[{now_et():%H:%M:%S} ET] cycle {cycle}/{args.minutes} — SPY lag {lags} — "
                    f"revisions: {sum(s['revisions'] for s in summary['per_symbol'].values())} — "
                    f"5m mismatches: {len(summary['nbis_5m_mismatches'])}"
                )
            time.sleep(max(0.0, CYCLE_SECONDS - (time.monotonic() - cycle_started)))

    print(json.dumps(probe.summary(), indent=2))


if __name__ == "__main__":
    main()
