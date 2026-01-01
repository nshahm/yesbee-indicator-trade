# 📈 Stock Trading System – Requirements Document

## 1️⃣ Objective

Build a **rule-based stock trading system** that:

* Identifies **trend and momentum**
* Generates **buy/sell signals** using indicators
* Applies **ATR-based Stop Loss and Trailing Stop Loss**
* Supports **swing and intraday trading**
* Is **backtestable and automation-ready**

---

## 2️⃣ Market Scope

| Parameter       | Value                 |
| --------------- | --------------------- |
| Market          | Indian Equity (NSE)   |
| Instrument      | Cash Market Stocks    |
| Trading Style   | Swing / Intraday      |
| Broker (Future) | Zerodha Kite / Upstox |

---

## 3️⃣ Timeframe Selection

| Purpose      | Timeframe |
| ------------ | --------- |
| Entry        | 15m / 30m |
| Confirmation | 1H / 1D   |
| Trend Bias   | Daily     |

---

## 4️⃣ Indicators Required

### 📊 Trend Indicators

| Indicator             | Settings | Purpose              |
| --------------------- | -------- | -------------------- |
| EMA                   | 20, 50   | Short & Medium trend |
| EMA                   | 200      | Long-term bias       |
| SuperTrend (Optional) | 10, 3    | Trend confirmation   |

---

### 📉 Momentum Indicator – RSI

| Parameter    | Value   |
| ------------ | ------- |
| Period       | 14      |
| Overbought   | 70      |
| Oversold     | 30      |
| Bullish Zone | 40 – 70 |
| Bearish Zone | 30 – 60 |

---

### 📏 Volatility Indicator – ATR

| Parameter | Value                     |
| --------- | ------------------------- |
| Period    | 14                        |
| Usage     | Stop Loss & Trailing Stop |

---

## 5️⃣ Entry Rules

### ✅ Long (Buy) Entry Conditions

All conditions must be satisfied:

1. **Trend Filter**

   * Price > EMA 50
   * EMA 20 > EMA 50

2. **RSI Condition**

   * RSI > 45
   * RSI is rising

3. **Price Action Confirmation**

   * Bullish candle OR
   * Bullish reversal pattern (Engulfing / Hammer / Pullback)

4. **Higher Timeframe Confirmation**

   * Price above EMA 50 on 1H or 1D timeframe

---

### ❌ Short / Sell Entry (Optional)

1. Price < EMA 50
2. EMA 20 < EMA 50
3. RSI < 55 and falling
4. Bearish candle confirmation

---

## 6️⃣ Stop Loss Rules (ATR Based)

### 🔴 Initial Stop Loss Calculation

```
Stop Loss = Entry Price − (ATR × SL_Multiplier)
```

| Trading Style | ATR Multiplier |
| ------------- | -------------- |
| Intraday      | 1.2 × ATR      |
| Swing         | 1.5 – 2 × ATR  |

---

## 7️⃣ Trailing Stop Loss Rules

### 🔁 Trailing Logic

```
Trailing SL = Highest Price − (ATR × Trail_Multiplier)
```

| Condition           | Action          |
| ------------------- | --------------- |
| New High Formed     | Trail SL upward |
| Pullback            | SL unchanged    |
| Price ≤ Trailing SL | Exit trade      |

Trail Multiplier: **1 – 1.5 × ATR**

---

## 8️⃣ Exit Conditions (Priority Order)

1. Stop Loss Hit
2. Trailing Stop Loss Hit
3. RSI reversal (RSI < 40 for long)
4. Trend breakdown (Close below EMA 50)
5. Time-based exit (Intraday session end)

---

## 9️⃣ Risk Management

### 💰 Capital Risk Rules

| Parameter       | Value  |
| --------------- | ------ |
| Risk per trade  | 1 – 2% |
| Max open trades | 3 – 5  |
| Daily max loss  | 3%     |

### 📐 Position Sizing Formula

```
Quantity = (Capital × Risk%) / (Entry − Stop Loss)
```

---

## 🔟 Trade Filters

* Avoid low-volume stocks
* Avoid major news / earnings days
* Skip trades when ATR is very low (sideways market)
* Trade only high-liquidity stocks

---

## 1️⃣1️⃣ Backtesting Requirements

### 📊 Performance Metrics

* Win Rate
* Risk–Reward Ratio
* Max Drawdown
* Expectancy
* Profit Factor

### 🔄 Optimization Variables

* ATR Multiplier (1.2 → 2.0)
* RSI thresholds (40/60, 45/55)
* EMA combinations

---

## 1️⃣2️⃣ Automation Readiness

### 🔌 System Modules

* Market Data Handler
* Indicator Engine
* Signal Generator
* Risk Manager
* Order Manager
* Trade Logger
* Alert System (Telegram / Email)

---

## 1️⃣3️⃣ Optional Enhancements

* Volume confirmation
* Sector strength filter
* Multi-timeframe analysis
* Partial profit booking
* AI-based trade scoring

---

## 📌 Strategy Summary

> **Trade with trend → Enter on RSI momentum → Protect using ATR stop loss → Trail profits using ATR**
