# No-Trade Day Detection Framework

## Purpose

This document defines a **rule-based framework** to identify **sideways / non-trending market days** and avoid low-probability trades. It is designed for **manual trading and automated trading systems**, especially for **intraday and options trading**.

---

## What is a No-Trade Day?

A **No-Trade Day** is when the market:

* Lacks clear directional movement (up or down)
* Shows low volatility and weak momentum
* Traps traders with false breakouts

**Goal:** Preserve capital by avoiding trades during these conditions.

---

## 1. Market Structure Filter (Primary)

### Definition

A trending market must form:

* **Uptrend:** Higher High (HH) + Higher Low (HL)
* **Downtrend:** Lower Low (LL) + Lower High (LH)

### No-Trade Condition

* Price overlaps previous candles
* No HH-HL or LL-LH in last 10–15 candles

### Logic

```pseudo
if NOT (higherHighs AND higherLows)
   AND NOT (lowerHighs AND lowerLows):
    market = SIDEWAYS
```

---

## 2. Volatility Compression Filter (ATR)

### Metric

* **ATR (14)** on trading timeframe

### No-Trade Condition

* Day / session range is too small

```text
(Session High − Session Low) < 0.6 × ATR(14)
```

### Logic

```pseudo
range = sessionHigh - sessionLow
if range < 0.6 * ATR(14):
    noTrade = true
```

---

## 3. ADX – Trend Strength Filter

### ADX Interpretation

| ADX Value | Market State   |
| --------- | -------------- |
| < 18      | Sideways ❌     |
| 18–25     | Weak Trend ⚠️  |
| > 25      | Strong Trend ✅ |

### No-Trade Condition

```pseudo
if ADX(14) < 18:
    noTrade = true
```

---

## 4. Moving Average Flatness Filter

### Indicators

* EMA 20
* EMA 50

### No-Trade Conditions

* EMA slopes near zero
* EMA20 and EMA50 overlapping
* Price crossing EMAs frequently

### Logic

```pseudo
if abs(EMA20 - EMA50) < smallThreshold
   AND emaSlope20 < slopeLimit
   AND emaSlope50 < slopeLimit:
    noTrade = true
```

---

## 5. RSI Choppiness Filter

### RSI Behavior in Sideways Market

* RSI oscillates between **45 – 55**
* No momentum expansion

### No-Trade Condition

```pseudo
if RSI(14) between 45 and 55 for last N candles:
    noTrade = true
```

---

## 6. Bollinger Band Squeeze Filter

### Indicator

* Bollinger Bands (20, 2)

### No-Trade Condition

* Narrow band width
* Price hugging middle band

### Logic

```pseudo
if BB_Width < SMA(BB_Width, 20) * 0.7:
    sideways = true
```

---

## 7. Volume Confirmation Filter

### Sideways Volume Traits

* Volume below average
* No volume expansion on break attempts

### No-Trade Condition

```pseudo
if volume < SMA(volume, 20):
    weakMarket = true
```

---

## 8. Time-Based No-Trade Zones (Intraday)

Avoid trading during:

* First **5–10 minutes** after market open
* **Midday low-activity zone (12:00 – 1:30 PM IST)**
* Before major news / economic events

```pseudo
if time in restrictedZone:
    noTrade = true
```

---

## 9. Composite No-Trade Decision Rule

Declare **NO-TRADE DAY** if **3 or more conditions** are true:

* ADX < 18
* Session range < 0.6 × ATR
* EMA flat / overlapping
* RSI between 45–55
* Bollinger Band squeeze
* Volume below average

### Final Logic

```pseudo
noTradeScore = count(trueConditions)

if noTradeScore >= 3:
    TRADE_MODE = "NO TRADE"
```

---

## 10. Options-Specific No-Trade Signals

### Warning Signs

* Both CE & PE premiums decaying
* IV falling continuously
* ATM straddle not expanding
* No directional candle on 15-min chart

**Action:** Avoid directional options trades.

---

## Best Practices

* No-trade days are **capital protection days**
* Missing trades is better than forced trades
* Sideways markets punish overtrading

> "Not trading is also a valid trade decision"

---

## Recommended Timeframes

| Trading Style | Timeframe |
| ------------- | --------- |
| Intraday      | 5m / 15m  |
| Swing         | 1H / 4H   |
| Confirmation  | Higher TF |

---

## End of Document
