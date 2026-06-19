# Self-Learning Market Attribution System
## Working Summary and Continuation Blueprint

Prepared from our discussion so nothing gets left behind.

## 1. Core Vision

The project is a self-learning market attribution system for stocks and options. The purpose is not simply to predict direction. The purpose is to identify why a stock, ETF, index, option chain, sector, or broader market instrument moved, what forces were behind the move, what happened before the move became obvious, and what historically tends to happen next under similar conditions.

The system should serve scalping, day trading, swing trading, and long-term portfolio investing from the same intelligence core. Each time horizon should use its own outcome windows, execution logic, risk rules, and feedback loop, but the underlying attribution brain should remain shared.

Core idea: build the engine underneath the chart, not another indicator, scanner, alert service, or basic buy/sell bot.

Working definition: A self-learning market attribution engine that detects, classifies, explains, tests, and improves its understanding of price movement across multiple time horizons.

## 2. The Main Belief Behind the System

Stocks do not move up and down for no reason. Every ebb, flow, spike, selloff, reversal, continuation, gap, squeeze, and repricing event leaves a footprint. This does not mean a traditional footprint chart. It means a hidden causal stack that may include price behavior, options positioning, dealer hedging, sector rotation, inverse ETF confirmation, macro conditions, liquidity, news, institutional behavior, volatility, and crowd psychology.

The visible reason is often not the full reason. A move may appear to be news-driven, but the true stack may look more like this:

```text
News headline = trigger
High short interest = fuel
Call buying = acceleration
Dealer hedging = continuation
Sector strength = support
Low liquidity = speed
Retail indicator reaction = liquidity pool
```

The engine should not force one explanation. It should create a weighted attribution model.

## 3. One Brain, Four Trading and Investing Heads

| Layer | Time Horizon | Main Question | Typical Outcome Windows |
|---|---|---|---|
| Scalping | Seconds to minutes | Is this immediate move real, fake, liquidity-driven, or continuation-worthy? | 1m, 3m, 5m, 15m, 30m |
| Day Trading | Intraday session | What is driving the move today and can it continue into the session? | 30m, 1h, 2h, end-of-day |
| Swing Trading | Days to weeks | Is this a larger repricing, reversal, breakout, or continuation setup? | 1d, 3d, 5d, 10d, 20d |
| Portfolio Investing | Months to years | Is the company being structurally repriced or accumulated? | 1m, 3m, 6m, 1y+ |

## 4. Maximum Freedom Inside a Disciplined Architecture

The engine should have broad freedom to ingest many forms of market data, test relationships, create features, generate hypotheses, and discover patterns without needing every relationship manually listed. However, the freedom must live inside a disciplined architecture. Unlimited data without structure becomes noise. Maximum freedom with strict testing, labeling, event sequencing, and forward validation becomes edge discovery.

## 5. Data Universe to Consider Long Term

- Stocks and ETFs: OHLCV, relative volume, dollar volume, ranges, gaps, VWAP, anchored VWAP, support/resistance.
- Options: chains, volume, open interest, IV, Greeks, skew, call/put behavior, gamma exposure, dealer hedging, expiration effects.
- Inverse and leveraged ETFs: SQQQ, TQQQ, SH, SDS, SOXS, SOXL, UVXY and related instruments for confirmation, divergence, stress, and hedging demand.
- Market internals: TICK, TRIN, ADD, VOLD, UVOL/DVOL, breadth, sector breadth, index breadth.
- Sectors and themes: XLK, XLF, XLV, XLE, SMH, XBI, IWM, DIA, sector leadership and rotation.
- Volatility products: VIX, VVIX, SKEW, term structure, volatility compression and expansion.
- Macro and cross-asset: rates, dollar, bonds, commodities, economic calendar, Fed events, risk-on/risk-off conditions.
- Catalysts: news, earnings, guidance, analyst actions, FDA, litigation, M&A, filings, corporate events.
- Positioning and liquidity: short interest, borrow, ETF flows, dark pool prints if available, liquidity vacuums, stop runs.
- Fundamentals and portfolio: revenue, margins, free cash flow, earnings quality, valuation, institutional ownership, structural repricing.

## 6. Event Timeline Layer: Sequence Is Everything

The system cannot understand cause unless it understands sequence. Every event needs a timestamped timeline.

```text
9:30 - Gap up 2.1%
9:33 - TICK confirms risk-on tone
9:35 - Sector ETF breaks high
9:37 - Call volume spikes before underlying breakout
9:39 - SQQQ fails to bounce while QQQ holds bid
9:41 - Stock reclaims VWAP
9:44 - Stock breaks opening range high
9:52 - IV expands and volume follows price
```

The engine should ask: which relationship changed first, which confirmed, which diverged, and which failed?

## 7. Relationship Engine

The system should study relationships, not just tickers in isolation.

```text
AAPL vs QQQ
AAPL vs XLK
AAPL vs MSFT/NVDA/AMZN peers
AAPL vs VIX/VVIX
AAPL vs dollar/rates
AAPL vs call IV and put IV
AAPL vs options volume and open interest
AAPL vs inverse tech ETFs
AAPL vs sector breadth
AAPL vs market internals
```

Inverse ETFs are especially useful for confirmation, divergence, hidden stress, hedging demand, and false moves.

## 8. Feature Factory

The feature factory should create thousands of candidate features from raw data, including relative volume, gap behavior, VWAP behavior, sector strength, beta-adjusted performance, IV changes, skew changes, gamma wall distance, TICK/TRIN/VOLD regimes, VIX/VVIX/SKEW structure, earnings/news proximity, and forward returns.

## 9. Self-Optimizing Indicator Discovery

Indicators should not be hardcoded as truth. They should be treated as candidate features whose parameters can be discovered, tested, validated, and retired if they decay. RSI is the clearest example discussed.

The engine should not ask only whether RSI works. It should ask: under what exact conditions does RSI work, with what settings, for what move type, in what market regime, on what timeframe, and with what confirmation stack?

## 10. RSI 14/70/30 as Retail Psychology, Not Truth

Standard RSI 14 with 70/30 overbought/oversold logic is part of the problem. It is public, crowded, and predictable. Institutions, hedge funds, and larger players understand that many retail traders react to these levels.

Therefore, the machine should treat RSI 14/70/30 less as a clean signal and more as a behavioral marker. It should ask what the market is doing around the place where retail traders are likely to react.

```text
RSI 14 oversold alone = low-quality signal.

RSI 14 oversold + bearish internals + sector weakness + expanding put IV = possible continuation lower.

RSI 14 oversold + failed breakdown + sector divergence + absorption + IV stabilization = reversal candidate.

RSI 14 overbought in a momentum repricing = possible strength, not an automatic short.
```

## 11. Hypothesis and Attribution Engine

The attribution engine should generate multiple possible explanations for a move, score them, and update the scores as new evidence arrives.

Example:

```text
Ticker: NVDA
Move: +3.2% intraday

Attribution:
- Options acceleration: 32%
- Semiconductor sector strength: 27%
- QQQ beta: 18%
- Short covering: 11%
- Volatility compression breakout: 8%
- News/catalyst: 4%

Confidence: 74%
Forward bias: continuation if sector, QQQ, IV, and VWAP remain supportive.
```

## 12. Labeling Engine

The machine cannot learn deeply if labels are shallow. Labels should not be limited to buy, sell, win, or loss. The system needs event-type labels and cause-type labels.

```text
MARKET_BETA_MOVE
SECTOR_ROTATION_MOVE
NEWS_CATALYST_MOVE
EARNINGS_REPRICE_MOVE
OPTIONS_GAMMA_MOVE
SHORT_COVERING_MOVE
LIQUIDITY_SWEEP_REVERSAL
INSTITUTIONAL_ACCUMULATION
INSTITUTIONAL_DISTRIBUTION
FAILED_BREAKOUT
VWAP_RECLAIM_CONTINUATION
OPENING_DRIVE
VOLATILITY_EXPANSION
RETAIL_TRAP_SIGNAL
INVERSE_ETF_DIVERGENCE
GAP_CONTINUATION
GAP_FADE
MULTI_DAY_COMPRESSION_BREAKOUT
```

## 13. Outcome Tracker

Every classified event must be tracked forward across multiple horizons: 5-minute, 15-minute, 30-minute, 1-hour, end-of-day, next-day, 3-day, 5-day, 10-day, 20-day, 60-day, 3-month, 6-month, and 1-year returns.

## 14. Testing Discipline: Avoid Curve Fitting

The system must use in-sample training, out-of-sample validation, walk-forward testing, regime testing, forward testing, decay monitoring, and kill switches for weak or decaying edges.

## 15. Scanner and Live Output Vision

Bad scanner output:

```text
AAPL is up 2.1%. Volume is high. RSI is overbought.
```

Target scanner output:

```text
AAPL is showing a sector-supported, options-accelerated, VWAP-reclaim continuation setup.
Call IV expanded before the breakout, XLK confirmed, QQQ beta is supportive, and inverse ETF confirmation is clean.
Similar historical setups produced positive 5-day continuation 67% of the time, with failure risk if QQQ loses trend or IV stalls.
```

## 16. Original Long-Term Build Phases

1. Market Event Recorder: collect, normalize, and timestamp all available market events.
2. Feature Factory: generate candidate features from price, options, internals, ETFs, inverse ETFs, sectors, volatility, news, and fundamentals.
3. Attribution Classifier: classify moves by likely cause and event type.
4. Outcome Tracker: track what happens after each event across multiple horizons.
5. Parameter Discovery: let the engine discover settings for RSI, MACD, VWAP, volatility, options, and other features.
6. Backtester: test whether historical attribution-plus-signal setups had edge.
7. Forward Tester: log live hypotheses before outcomes happen.
8. Live Scanner: surface current setups that match proven historical patterns.
9. Strategy Heads: apply the attribution brain to scalp, day, swing, and portfolio models.

## 17. Core Design Principles

- Do not teach the system what to think. Teach it how to investigate.
- Every popular retail signal should be treated as a possible trap, not an automatic entry.
- Indicators are candidate features, not authority.
- RSI 14/70/30 should be studied as crowd behavior and liquidity psychology.
- Sequence matters. Every relevant event must be timestamped.
- Attribution should be weighted, not binary.
- The system should learn when a signal works, when it fails, why it works, and when the edge decays.
- Backtesting is not enough. Forward testing is mandatory.
- The first goal is the best explanation engine possible.

## 18. Current Decision: Narrow the First Build

The first implementation should not attempt to build every scanner at once. The correct first move is to focus on one complete scanner and get it as close to perfect as possible before adding more layers.

The first scanner will be a swing trading scanner, signal engine, backtester, forward tester, and self-learning research engine centered on RSI behavior and daily historical data.

Important boundary: no options data in Version 1. Options, gamma, IV, skew, dealer hedging, and options flow will be added later after the first swing scanner works end to end.

## 19. Version 1 Name and Objective

Working name: RSI Swing Reversal Self-Learner.

Version 1 objective: build a Python-based swing trading self-learning scanner that studies daily historical stock data, discovers better RSI parameters and confirmation rules, backtests them, walk-forward tests them, produces current scanner signals, and logs forward results.

The scanner should not say: RSI 14 is oversold, buy.

It should say: for this stock, under this market condition, this RSI structure has historically produced a high-probability swing reversal over the next 5, 10, or 20 trading days.

## 20. Why Version 1 Should Focus on Swing Trading Only

- Swing trading gives enough data per ticker to study meaningful daily patterns.
- Daily bars are cleaner than noisy 1-minute scalping data for the first build.
- The feedback window is manageable: 3-day, 5-day, 10-day, and 20-day outcomes.
- We can prove the full research loop before adding intraday complexity.
- It avoids scope creep and lets us finish one scanner from data to signal to forward journal.
- It creates a reusable pattern that later scanners can copy.

## 21. Version 1 Data Scope

Use daily data only at first.

Included:

- OHLCV.
- Adjusted close.
- Volume and relative volume.
- ATR and volatility regime.
- Moving averages: 20, 50, 100, 200.
- Distance from moving averages.
- Recent highs and lows.
- Drawdown from recent high.
- Bounce from recent low.
- Candle structure.
- SPY and QQQ market trend filters.
- Optional sector ETF filter later in Version 1.5.

Excluded from Version 1:

- Options data.
- Gamma exposure.
- IV, skew, Greeks, OI, dealer hedging.
- Intraday market internals.
- Live execution.
- News and NLP.
- Deep learning and reinforcement learning.

## 22. First Universe of Symbols

Start with a focused research universe, then expand.

Suggested first universe:

```text
SPY
QQQ
AAPL
MSFT
NVDA
TSLA
AMD
META
AMZN
GOOGL
```

Expansion universe can later include liquid large caps, sector ETFs, leveraged ETFs, inverse ETFs, and high-beta names.

## 23. RSI Self-Learning Research Questions

The engine should not ask whether RSI works. It should ask:

- Which RSI length works best for this ticker and regime?
- Which RSI level matters most: absolute value, slope, cross, compression, divergence, or failure swing?
- Does RSI work better in trend, chop, high volatility, low volatility, or after large selloffs?
- Is RSI 14 a useful control group or just a crowd-behavior marker?
- Does the edge come from the RSI value itself, or from what price does after everyone sees RSI overbought or oversold?
- Which confirmation stack improves RSI the most?
- Which settings decay over time and should be retired?

## 24. RSI Parameter Discovery Search Space

The system should test RSI as a flexible structure.

Search space:

- RSI length: 2 to 50.
- Lower trigger zone: 5 to 60.
- Upper trigger zone: 40 to 95.
- RSI slope windows: 1, 2, 3, 5, 10 bars.
- RSI smoothing: none, short smoothing, medium smoothing.
- RSI cross behavior: cross above learned zone, cross below learned zone, reclaim after oversold, reject after overbought.
- RSI divergence: price lower low with RSI higher low, price higher high with RSI lower high.
- RSI failure swing behavior.
- RSI compression and expansion.
- RSI relative to trend regime.

RSI 14/70/30 should remain in the dataset as a baseline and retail psychology feature, not as the default trading rule.

## 25. Confirmation Features for Version 1

Version 1 should test RSI with confirmation features, not RSI alone.

Initial confirmation features:

- Price above or below 20, 50, 100, 200 moving averages.
- Moving average slope.
- Price distance from moving averages.
- ATR percentile.
- Relative volume.
- Large red candle exhaustion.
- Multi-day pullback count.
- Failed breakdown below prior low.
- Reclaim of prior low.
- Close position inside daily range.
- Gap up or gap down behavior.
- SPY trend filter.
- QQQ trend filter.
- Market regime: bullish, bearish, sideways, high volatility, low volatility.

## 26. Labeling Engine for Swing Signals

The system needs labels that measure real swing outcomes.

Possible labels:

- Did price rise at least 3% within 10 trading days?
- Did price rise at least 5% within 20 trading days?
- Did price hit 2R before -1R?
- Did price close higher after 3, 5, 10, or 20 trading days?
- What was maximum favorable excursion?
- What was maximum adverse excursion?
- Did price break below the signal candle low?
- Did price hold the reversal structure?
- Did the setup fail immediately?
- Was the move a reversal, bounce, continuation, or failed signal?

The system must not label only buy, sell, win, or loss. It needs outcome labels plus structure labels.

## 27. Backtesting Rules for Version 1

The backtester should test every candidate rule using honest historical simulation.

Rules to include:

- No future leakage.
- Enter only after the signal is known.
- Test realistic next-day open or next-day close entry assumptions.
- Include transaction costs and slippage assumptions later.
- Track holding periods: 3, 5, 10, 20, and 30 trading days.
- Track stop methods: signal candle low, ATR stop, percentage stop, and time stop.
- Track profit methods: fixed R, trailing stop, time exit, and close-based exit.

Do not rank results only by win rate.

Rank by:

- Win rate.
- Average return.
- Median return.
- Expectancy.
- Profit factor.
- Max drawdown.
- Average max adverse excursion.
- Average max favorable excursion.
- Number of trades.
- Consistency across years.
- Out-of-sample performance.
- Walk-forward performance.

## 28. Walk-Forward and Anti-Curve-Fitting Rules

The machine must not be allowed to fool itself.

Rules:

- Never trust a setting just because it worked on one stock.
- Never trust a setting just because it worked during one market regime.
- Never trust a setting unless it survives out-of-sample testing.
- Never trust a setting unless it survives walk-forward testing.
- Never trust a setting unless it has enough trades to matter.
- Never trust a setting unless forward testing confirms it.
- Track edge decay and retire weak settings.
- Compare every custom setting against naive RSI 14/70/30 and against simple buy-and-hold.

## 29. Forward Tester Journal

The forward tester is mandatory. It should log every live or paper signal before the outcome is known.

Forward test journal fields:

```text
date
ticker
signal_type
rsi_model_version
rsi_length
rsi_trigger_zone
confirmation_stack
market_regime
entry_reference
stop_reference
target_reference
confidence_score
historical_similarity_count
historical_win_rate
historical_average_return
actual_3d_return
actual_5d_return
actual_10d_return
actual_20d_return
max_favorable_excursion
max_adverse_excursion
result_label
notes
```

The system must never rewrite history after a signal is logged.

## 30. Scanner Output Target for Version 1

The scanner output should be evidence-based.

Example:

```text
Ticker: NVDA
Signal Type: Swing Reversal
Date: 2026-06-19
Model: RSI Swing Reversal Self-Learner v1
Confidence: 82%

Learned Setup:
- RSI custom length entered learned reversal zone.
- RSI slope turned positive.
- Price held above 50-day trend structure.
- ATR volatility is inside favorable range.
- Relative volume confirms participation.
- SPY and QQQ market filters are supportive.

Historical Similarity:
- Similar setups: 184
- 10-day win rate: 71%
- 20-day win rate: 76%
- Average 20-day return: 6.4%
- Average max adverse move: -2.1%

Research Bias:
Bullish swing reversal candidate.
Invalidation: break below signal candle low or model stop.
```

## 31. Python Stack Decision for Version 1

Python is the correct first choice because the data science, ML, optimization, time-series, and research tooling ecosystem is strongest there.

Recommended stack:

- Python.
- pandas for data handling.
- NumPy for numerical operations.
- Polars later if datasets get larger.
- scikit-learn for time-series-aware modeling and validation.
- Optuna for parameter discovery and optimization.
- matplotlib for research plots.
- SQLite or DuckDB later for structured local storage.
- Parquet files for historical datasets and feature stores.

Do not start with deep learning or reinforcement learning. Start with transparent research, optimization, backtesting, and forward testing.

## 32. Version 1 Repository Structure

```text
swing-rsi-self-learner/
  README.md
  requirements.txt
  pyproject.toml

  data/
    raw/
    processed/
    features/
    signals/
    forward_tests/

  src/
    config.py
    data_loader.py
    feature_engine.py
    rsi_engine.py
    label_engine.py
    backtester.py
    optimizer.py
    walk_forward.py
    scanner.py
    forward_tester.py
    reports.py

  notebooks/
    01_data_check.ipynb
    02_rsi_research.ipynb
    03_backtest_review.ipynb

  reports/
    scanner_results.csv
    backtest_summary.csv
    forward_test_journal.csv
```

Heart of the first version:

```text
rsi_engine.py
optimizer.py
backtester.py
walk_forward.py
scanner.py
forward_tester.py
```

## 33. Version 1 Done Criteria

Version 1 is not done when it produces a chart. It is done when it completes the full research loop.

Done means:

- Historical daily data loads correctly.
- RSI variations are generated correctly.
- Confirmation features are generated correctly.
- Labels are created without future leakage.
- Backtester runs honestly.
- Optimizer finds candidate RSI structures.
- Walk-forward validation filters out curve-fitted settings.
- Scanner produces current swing candidates.
- Forward tester logs every signal before outcomes are known.
- Reports clearly show what worked, what failed, and what needs to be killed.

## 34. Immediate Engineering Next Step

Build the first repo skeleton for the RSI Swing Reversal Self-Learner.

First engineering target:

```text
Create a Python project that can:
1. download or load daily OHLCV data,
2. calculate many RSI variants,
3. create basic swing outcome labels,
4. run a simple parameter search,
5. produce a backtest summary,
6. output scanner candidates,
7. create a forward-test journal file.
```

No options yet. No live execution yet. No complex NLP yet. Get the first scanner working end to end, then expand.

## 35. Current Simplified Mission Statement

Build one elite swing trading self-learning scanner first.

Use daily price and volume data. Let the engine discover RSI behavior and confirmation rules through historical testing. Validate everything out-of-sample and walk-forward. Log all future signals before outcomes happen. Once this is proven, use the same engine pattern to add other scanners, options data, internals, inverse ETFs, NLP, and portfolio logic.
