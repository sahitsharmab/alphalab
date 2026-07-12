# Sprint M1a Intraday Provider Scorecard

Date: 2026-07-12  
Status: **Blocked — no provider selected; M1b not started**

## Verification Boundary

This pre-task was run on a Sunday. Historical responses could be tested, but live premarket, regular-session, and after-hours observation delay could not be measured. No Alpaca, Massive/Polygon, or Alpha Vantage credentials were present in the local environment. Authentication failures are not provider failures; they are unverified acceptance criteria.

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

## Decision

No provider satisfies every M1a acceptance criterion yet.

* **Alpaca Basic / IEX:** leading candidate, blocked on free credentials and a live-session test. NBIS IEX sparsity, volume coverage, completed-bar latency, and extended-hours usefulness remain unknown.
* **Yahoo intraday:** passes recent regular-session continuity and 1m-to-5m reconciliation. It fails selection today because live delay and incomplete-bar behavior were not measurable, extended-hours volume is unusable, and the endpoint has no supported contract/licensing assurance.
* **Massive Basic:** rejected as M1 primary because the free plan is end-of-day. It remains a possible historical validation source.

M1b must not start until a weekday run observes premarket, regular, and after-hours behavior and free Alpaca credentials are available.

## Official Documentation Reviewed

* [Alpaca market-data plans](https://docs.alpaca.markets/us/docs/about-market-data-api)
* [Alpaca IEX versus SIP FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
* [Massive stock aggregates](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
* [Massive stock API overview](https://massive.com/docs/rest/stocks)
* [Alpha Vantage intraday documentation](https://www.alphavantage.co/documentation/)
