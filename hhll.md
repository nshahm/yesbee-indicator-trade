# Market Structure Detection for CALL & PUT Trades

This document defines **best practices and automation-ready logic** to detect:

* **PUT trades:** Higher High → Lower High → Breakdown
* **CALL trades:** Lower Low → Lower High → Breakout

Designed for **algorithmic trading systems**, especially for **options trading**.

---

## 1. Core Market Structure Definitions (Algo-Safe)

### Swing High

A candle whose **high is greater than N candles on both sides**.

```text
High[i] > High[i-1..i-N] AND High[i] > High[i+1..i+N]
```

### Swing Low

```text
Low[i] < Low[i-1..i-N] AND Low[i] < Low[i+1..i+N]
```

**Recommended Parameters**

* Intraday: N = 2 or 3
* Swing Trading: N = 3 to 5

---

## 2. PUT Trade Structure (HH → LH → Breakdown)

### Market Meaning

Uptrend **losing momentum**, sellers entering at lower prices.

### Required Structure

```
Higher High (HH)
   ↓
Lower High (LH)
   ↓
Break below last Higher Low (HL)
```

### Mandatory Conditions

| Condition                 | Purpose                |
| ------------------------- | ---------------------- |
| HH formed                 | Confirms prior uptrend |
| LH below HH               | Buyer weakness         |
| Close below HL            | Structure break        |
| Volume expansion          | Seller confirmation    |
| RSI < 50                  | Momentum shift         |
| Price below VWAP / 20 EMA | Trend alignment        |

---

### PUT Trade Logic (Automation)

#### Detect Higher High

```pseudo
if swingHigh[i] > previousSwingHigh:
    mark HH
```

#### Detect Lower High

```pseudo
if swingHigh[j] < HH AND swingHigh[j] > lastSwingLow:
    mark LH
```

#### Entry Trigger

```pseudo
if close < lastSwingLow AND volume > avgVolume:
    PUT_ENTRY = true
```

### Stop Loss

```text
SL = LH_high + ATR(14) * 0.3
```

### Target

```text
Target = Entry - (HH - HL) OR ATR-based trailing
```

---

## 3. CALL Trade Structure (LL → LH → Breakout)

### Market Meaning

Downtrend **losing selling pressure**, buyers absorbing supply.

### Required Structure

```
Lower Low (LL)
   ↓
Lower High (LH)
   ↓
Break above LH
```

### Mandatory Conditions

| Condition                 | Purpose                  |
| ------------------------- | ------------------------ |
| LL formed                 | Confirms prior downtrend |
| LH formed                 | Seller weakness          |
| Close above LH            | Structure break          |
| RSI > 50                  | Momentum shift           |
| Price above VWAP / 20 EMA | Trend reversal           |
| No nearby resistance      | Clean breakout           |

---

### CALL Trade Logic (Automation)

#### Detect Lower Low

```pseudo
if swingLow[i] < previousSwingLow:
    mark LL
```

#### Detect Lower High

```pseudo
if swingHigh[j] < previousSwingHigh:
    mark LH
```

#### Entry Trigger

```pseudo
if close > LH AND volume > avgVolume:
    CALL_ENTRY = true
```

### Stop Loss

```text
SL = LL_low - ATR(14) * 0.3
```

### Target

```text
Target = Entry + (LH - LL) OR ATR-based trailing
```

---

## 4. Multi-Timeframe Confirmation (Highly Recommended)

**Best Practice**

* Higher Timeframe (15m / 30m): Directional bias
* Lower Timeframe (3m / 5m): Entry execution

### Example

```text
15m → HH-LH → Bearish bias
5m  → Breakdown → PUT entry
```

---

## 5. False Signal Protection

Avoid trades if:

* Structure forms inside a range
* ATR is contracting (low volatility)
* RSI divergence against trade
* Sudden news/event candle

---

## 6. End-to-End Automation Flow

```pseudo
detectSwings()

if trend == UP:
    if HH and LH and close < HL:
        confirm volume and RSI
        enter PUT

if trend == DOWN:
    if LL and LH and close > LH:
        confirm volume and RSI
        enter CALL
```

---

## 7. Options Trading Notes (India Market)

* Prefer ATM or slightly ITM options
* Best entries before 12:30 PM
* Avoid new structure trades after 3:00 PM
* Combine with OI buildup for higher accuracy

---

## 8. Future Extensions

* State-machine based structure engine
* Pine Script implementation
* Python backtest module
* Zerodha Kite API automation

---

**End of Document**
