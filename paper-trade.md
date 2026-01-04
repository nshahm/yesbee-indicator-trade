# paper-trade-requirement.md

## Paper Trading Implementation – Zerodha Kite Integration

## 1. Objective

The objective of this document is to define the requirements for implementing a **real-time paper trading system** integrated with **Zerodha Kite**, where live market candles are received and analyzed using **existing automation trading logic** (not historical backtesting). The system should simulate trades, display actionable paper trades via a UI, and maintain complete trade history and performance analytics.

---

## 2. Scope

### In Scope

* Real-time candle data ingestion from Zerodha Kite
* Applying existing automated trading logic on live candles
* Paper trade signal generation (Call / Put / Buy / Sell)
* Virtual order execution and trade lifecycle management
* UI screens for trade execution, monitoring, and history
* Performance metrics and reporting

### Out of Scope

* Actual order placement in Zerodha
* Historical backtesting engine
* Portfolio margin or capital optimization
* Brokerage and tax calculations

---

## 3. High-Level Architecture

```
Zerodha Kite WebSocket
        ↓
Live Candle Builder
        ↓
Existing Automation Logic Engine
        ↓
Paper Trade Engine
        ↓
Database
        ↓
UI Dashboard
```

---

## 4. Zerodha Kite Integration Requirements

### 4.1 Authentication

* Support Zerodha Kite OAuth flow
* Secure storage of:

  * API Key
  * Access Token
* Auto token refresh handling

### 4.2 Market Data

* Use **Kite WebSocket** for live tick data
* Convert ticks into timeframe-based candles:

  * 1m (mandatory)
  * 3m, 5m, 15m (configurable)

### 4.3 Instruments Supported

* Equity (Cash Market)
* Index Options (NIFTY, BANKNIFTY, FINNIFTY)
* Stock Options (Phase 2)

---

## 5. Candle Processing Engine

### Requirements

* Aggregate tick data into OHLC candles
* Maintain rolling candle buffer per symbol
* Ensure candle completeness before analysis
* Handle market gaps and reconnect scenarios

### Configurations

* Timeframe selection
* Trading session time (e.g., 9:15 – 3:15)

---

## 6. Automation Logic Integration

### Key Principle

> **Reuse existing automation logic exactly as-is**, replacing only the data source from historical candles to live candles.

### Logic Inputs

* OHLC candles
* Indicators (RSI, ADX, MACD, ATR, etc.)
* Market structure signals
* Candlestick patterns
* Trend & no-trade detection logic

### Logic Outputs

* Trade Signal:

  * Instrument
  * Direction (Buy / Sell | Call / Put)
  * Entry Price
  * Stop Loss
  * Target
  * Confidence / Score

---

## 7. Paper Trade Engine

### 7.1 Trade Creation

* Create virtual trades on signal confirmation
* Configurable rules:

  * One trade per instrument
  * Cooldown period after exit
  * Max trades per day

### 7.2 Virtual Execution

* Entry price options:

  * Candle close price
  * Next candle open
* Simulate:

  * Market orders
  * Slippage (optional)

### 7.3 Trade Lifecycle

States:

* SIGNAL_GENERATED
* WAITING_FOR_EXECUTION
* OPEN
* PARTIAL_EXIT (optional)
* CLOSED
* CANCELLED

### 7.4 Exit Logic

* Stop Loss hit (ATR-based or fixed)
* Target hit
* Trailing stop loss
* Signal reversal
* Market close auto-exit

---

## 8. Risk Management (Paper Level)

* Virtual capital configuration
* Risk per trade (%)
* Max drawdown per day
* Trade blocking after loss limit reached

---

## 9. UI / UX Requirements

### 9.1 Paper Trade Execution Screen

**Purpose:** Display live paper trade opportunities before execution

Fields:

* Symbol
* Instrument Type (Equity / Option)
* Direction (Call / Put / Buy / Sell)
* Entry Price
* Stop Loss
* Target
* Risk-Reward Ratio
* Signal Time
* Strategy Name
* Action Button:

  * Execute Paper Trade
  * Ignore

---

### 9.2 Active Paper Trades Screen

**Purpose:** Monitor ongoing paper trades

Fields:

* Symbol
* Entry Price
* Current LTP
* Unrealized P&L
* Stop Loss
* Target
* Trailing SL
* Duration in Trade
* Status

Actions:

* Manual Exit
* Modify SL / Target (optional)

---

### 9.3 Paper Trade History Screen

**Purpose:** View completed paper trades

Filters:

* Date range
* Strategy
* Instrument
* Win / Loss

Fields:

* Entry Time
* Exit Time
* Entry Price
* Exit Price
* P&L
* Max Favorable Excursion (MFE)
* Max Adverse Excursion (MAE)
* Exit Reason

---

### 9.4 Performance & Results Dashboard

Metrics:

* Total Trades
* Win Rate (%)
* Profit Factor
* Expectancy
* Max Drawdown
* Strategy-wise performance

Visuals:

* Equity curve
* Daily P&L chart
* Win vs Loss distribution

---

## 10. Database Requirements

### Core Tables

* instruments
* candles
* paper_trades
* trade_events
* strategy_logs
* performance_summary

### Data Retention

* Candle data: Configurable (e.g., last 30 days)
* Trade history: Permanent

---

## 11. Configuration & Settings

* Enable / disable strategies
* Timeframe selection
* Risk parameters
* Trading hours
* No-trade day rules

---

## 12. Error Handling & Reliability

* WebSocket disconnect recovery
* Data consistency checks
* Duplicate candle prevention
* Trade execution idempotency

---

## 13. Logging & Audit

* Signal generation logs
* Trade decision logs
* Indicator snapshots at entry
* Reason for trade acceptance / rejection

---

## 14. Security

* Encrypted token storage
* Role-based UI access (Admin / Viewer)
* Read-only mode for analysis

---

## 15. Success Criteria

* Paper trades match logic behavior of live automation
* Zero dependency on historical backtesting
* Accurate P&L simulation
* Clear visibility of signals, execution, and results

---

## 16. Future Enhancements

* Side-by-side Paper vs Live trade comparison
* Strategy optimizer using paper trade data
* ML-based signal scoring
* Auto promotion of paper strategies to live trading

---

**End of Document**
