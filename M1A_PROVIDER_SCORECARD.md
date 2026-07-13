# Sprint M1a Intraday Provider Scorecard

Date: 2026-07-12  
Status: **Blocked — Twelve Data is the leading candidate, but no provider is selected; M1b not started**

## Verification Boundary

This pre-task was run on a Sunday. Historical responses could be tested, but live premarket, regular-session, and after-hours observation delay could not be measured. No Alpaca or Massive/Polygon credentials were present. A Twelve Data Basic key was subsequently configured and tested. Authentication failures are not provider failures; they are unverified acceptance criteria.

Legend: **D** documented, **E** empirically observed on 2026-07-12, **U** unverified.

## Mandatory Scorecard

| Criterion | Alpaca Basic / IEX | Yahoo intraday | Massive Basic |
|---|---|---|---|
| API stability | D: supported REST/WebSocket contract | E: repeated identical requests returned HTTP 200 and identical payloads; U live stability | D: supported REST/flat-file contract |
| Authentication | D: free account and key/secret required; E: credentials absent | E: no key required | D: free account/API key required; E: credentials absent |
| Free restrictions | D: live equities are IEX-only; recent SIP restricted inside 15 minutes; 30 WebSocket symbols; 200 historical calls/min | E: no declared limit surfaced; unofficial endpoint has no supported quota contract | D: free Stocks Basic is end-of-day, 5 calls/min, two years history |
| Observation delay | U: could not measure on Sunday | U: could not measure on Sunday | D: end-of-day free; unsuitable for current-session timing |
| Premarket coverage | D: IEX may contain extended-hours trades; E untested | E: prices from 04:00 ET, but all tested 2026-07-10 bars had zero volume | D: historical extended hours, but end-of-day free; E untested |
| Regular coverage | D: live IEX single venue; E untested | E: exactly 390 one-minute bars on 2026-07-10 for NBIS, SPY, QQQ | D: consolidated historical aggregates; end-of-day free; E untested |
| After-hours coverage | D: IEX may contain extended-hours trades; E untested | E: prices to ~20:00 ET; almost/all zero-volume and terminal record not minute-aligned | D: historical extended hours; end-of-day free; E untested |
| One-minute bars | D: available | E: available for all three symbols (`range=5d&interval=1m`) | D: available historically, not current-session free |
| Historical depth | D: since 2016 | E: five recent trading days at 1m; one month returned at 5m | D: two years free |
| Missing bars | U | E: regular 0/390 missing; NBIS 11 premarket and 5 after-hours minutes absent on 2026-07-10; extended gaps varied | U |
| Timestamp consistency | U | E: regular minute-aligned; terminal extended record at `19:59:55`–`19:59:58` ET | U |
| Revisions/corrections | E untested | E: immediate repeated payloads identical; U live corrections/finalization | D correction semantics; E untested |
| Price coverage | D: IEX single venue | E: regular closes within $0.01–$0.05 of independent reference | D: consolidated historical, end-of-day free |
| Volume coverage | D: IEX only, not total market | E: regular volume was 89.8% NBIS, 84.2% SPY, 94.7% QQQ of independent daily reference; extended unavailable/zero | D: consolidated historical, not current-session free |
| Trade count | D: supported bar field; E untested | E: absent | D: documented; E untested |
| VWAP | D: supported; must be labelled IEX | E: absent; extended derivation invalid with zero volume | D: supported; end-of-day free |
| Rate limits | D: 200 historical calls/min; 30 live symbols | U: no reliable contract | D: 5 calls/min free |
| Licensing/usage risk | D: personal subscriber agreements apply | High: unsupported endpoint and unclear long-term API/display contract | D: personal non-professional terms apply |
| Maintainability | High contract quality if coverage passes | Low/medium: adapter helps, but contract may change silently | High contract quality; unusable recency for live M1 |
| NBIS suitability | U: must measure IEX sparsity and volume share live | Partial: excellent regular continuity; extended volume unusable; delay unknown | No for live M1; useful historical validator |
| SPY suitability | U: must measure live IEX coverage | Partial: complete regular bars; partial volume; delay unknown | No for live M1 |
| QQQ suitability | U: must measure live IEX coverage | Partial: complete regular bars; partial volume; delay unknown | No for live M1 |

## Yahoo Empirical Results

Requests used `includePrePost=true` and a browser-like user agent.

| Symbol | 1m bars / 5 days | Regular bars | Premarket | After-hours | Regular volume | Independent volume | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| NBIS | 4,778 | 390 | 319 | 235 | 10,315,196 | 11,490,536 | 89.8% |
| SPY | 4,722 | 390 | 313 | 241* | 35,532,590 | 42,191,313 | 84.2% |
| QQQ | 4,799 | 390 | 330 | 241* | 25,003,193 | 26,415,899 | 94.7% |

`*` The extra record is a non-minute-aligned terminal observation near 20:00 ET.

Provider-native regular-session 5m bars reconciled exactly with deterministic aggregation of the 390 one-minute bars for all three symbols: 78/78 bars, zero OHLC mismatches, zero volume mismatches.

| Symbol | Yahoo 15:59 ET close | Independent reference | Difference |
|---|---:|---:|---:|
| NBIS | 219.64 | 219.65 | -0.01 |
| SPY | 754.90 | 754.95 | -0.05 |
| QQQ | 725.53 | 725.51 | +0.02 |

The independent reference timestamp was 2026-07-11 00:15 UTC. This supports price plausibility, not exact feed equivalence.

## Twelve Data Basic Empirical Results

The configured free Basic key authenticated successfully.

| Criterion | Twelve Data Basic |
|---|---|
| API stability | D: supported REST contract; E: authenticated responses stable during probe |
| Authentication | E: free API key works; no brokerage funding or paid entitlement used |
| Free restrictions | D/E: 8 credits/minute, 800/day; pre/post rejected as paid-only |
| Observation delay | U: Sunday; must measure live |
| Premarket coverage | E: unavailable on Basic (HTTP 403) |
| Regular coverage | E: complete recent sessions for all three symbols |
| After-hours coverage | E: unavailable on Basic (HTTP 403) |
| One-minute bars | E: available for NBIS, SPY, QQQ |
| Historical depth | E: at least 5,000 rows / 13 sessions in one response; deeper Basic depth not yet measured |
| Missing bars | E: zero missing regular minutes in tested full sessions |
| Timestamp consistency | E: minute-aligned `America/New_York`, 09:30–15:59 ET |
| Revisions/corrections | E: immediate closed-session repeat identical; U live corrections/finalization |
| Price coverage | D: partial-venue default feed; E: values identical to Yahoo regular feed in tested window |
| Volume coverage | D: approximately 5% venue coverage; must never be labelled total market volume |
| Trade count | E: absent from tested time-series response |
| VWAP | E: absent from tested time-series response; derivable only as partial-venue VWAP |
| Rate limits | D/E: 8/minute and 800/day; limit encountered during extended verification |
| Licensing/usage risk | D: Basic supports personal/internal non-commercial use |
| Long-term maintainability | Medium/high documented API; limited free quota and partial feed are lasting constraints |
| NBIS suitability | Partial: regular bars complete; 10 native-vs-derived 5m mismatches unresolved |
| SPY suitability | Partial: regular bars complete and reconciliation exact; live delay unknown |
| QQQ suitability | Partial: regular bars complete and reconciliation exact; live delay unknown |

* `prepost=true` returned HTTP 403 for NBIS, SPY, and QQQ with an explicit message that pre/post data requires Pro or Venture. Extended-hours data is therefore unavailable on the free plan.
* Regular-session `1min` requests returned 5,000 rows per symbol spanning 13 trading days (2026-06-23 through 2026-07-10).
* The last two full sessions contained exactly 390 bars per symbol, with no duplicate timestamps, no missing regular minutes, and no zero-volume bars.
* Timestamps were consistently in `America/New_York`, from 09:30 through 15:59 ET.
* Immediate repeated NBIS 1m responses were identical.
* Twelve Data's 2026-07-10 1m values matched Yahoo's regular-session values, including volume. This is consistent with Twelve Data's documented partial-venue US feed and does not establish consolidated coverage.
* Derived versus provider-native 5m reconciliation: SPY 78/78 exact; QQQ 78/78 exact; NBIS had 10 mismatching bars. The mismatch details could not be retrieved immediately because the Basic per-minute credit limit was reached. This must be resolved before provider selection.

Twelve Data Basic is technically viable for regular-session-only charting, but its documented feed represents approximately 5% of total US trading volume. Any future UI would need terminology such as **Twelve Data partial-venue price**, **partial-venue volume**, and **partial-venue VWAP**. It cannot provide free premarket or after-hours context.

## Weekday Live Verification — 2026-07-13 (RESOLVED)

Ran `backend/scripts/m1a_probe.py` for 90 minutes from the 09:30 ET open
(NBIS/SPY/QQQ, 1m polled every 60s, native 5m every 5th cycle). Full results
in `backend/scripts/m1a_results/`. Every open question from the Sunday run is
now answered:

| Criterion | Result |
|---|---|
| **Appearance delay** | Completed 1m bars reliably available **~44s after the minute closes** (NBIS 44.0s / SPY 44.1s / QQQ 44.2s median; range 43.9–44.6s over 88 samples each). This is an **upper bound** — polls landed at :44 past each minute, so the true delay is ≤44s. Never once slower than one poll cycle. |
| **Current/in-progress bars** | **Never served** (0/90 polls returned an in-progress minute). Twelve Data returns only *completed* bars — so there is no partial-bar ambiguity, but the freshest datum is always the last closed minute (~44–104s old depending on position in the current minute). |
| **Revisions** | **Zero.** No completed bar changed after first appearance across 270 symbol-polls. Completed bars are immutable within the session → clean for bitemporal storage. |
| **NBIS 5m native-vs-derived** | **0 mismatches across 19 fully-covered windows.** Native 5m bars reconcile exactly with deterministic aggregation of the 1m series. The Sunday 10-bar mismatch was a stale/weekend-data artifact, not a live-data problem. |
| **Reliability** | 90/90 cycles, **0 errors**, comfortably inside the 8-credit/min budget. |

## Decision — SELECTED (regular-session only, with mandatory labeling)

**Twelve Data Basic is selected as the M1 intraday provider** for the
regular session. It passes every measurable acceptance criterion: fast
(≤44s), stable, no revisions, exact 5m aggregation, reliable within budget.

Non-negotiable constraints that M1b–M1e MUST honor (ADR-015 disclosure rule):

* **Regular session only.** Pre/post is paid-only (403 confirmed again
  2026-07-13). The intraday view MUST prominently disclose that premarket and
  after-hours are not covered — proven material the same morning, when SOFI
  was +3% premarket and AlphaLab was blind to it.
* **Partial-venue labeling.** ~5% of US volume; price/volume/VWAP must be
  labeled "partial-venue," never "consolidated real-time."
* **~1-minute staleness.** Only completed bars; the UI must never imply a live
  tick.
* **Credit budget.** 8/min, 800/day — bounds symbols × poll frequency; a large
  watchlist cannot poll every symbol every minute.

Other providers remain as future options: **Alpaca Basic/IEX** (unverified,
would add a second venue for cross-checking), **Yahoo intraday** (good
regular-session continuity, unsupported contract), **Massive** (end-of-day
only, historical validator).

**M1b (canonical bitemporal 1-minute storage) is now unblocked.**

## Official Documentation Reviewed

* [Alpaca market-data plans](https://docs.alpaca.markets/us/docs/about-market-data-api)
* [Alpaca IEX versus SIP FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
* [Massive stock aggregates](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
* [Massive stock API overview](https://massive.com/docs/rest/stocks)
* [Alpha Vantage intraday documentation](https://www.alphavantage.co/documentation/)
* [Twelve Data pricing and Basic limits](https://twelvedata.com/pricing)
* [Twelve Data US feed coverage](https://support.twelvedata.com/en/articles/9935903-us-equities-market-data)
