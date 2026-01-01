# Stop Loss & Trailing Stop Loss Strategy

## Objective

Reduce losses while maximizing profits using a **rule-based, volatility-adaptive, and structure-aware** stop loss framework.

---

## 1. Core Principle

> **Stop Loss protects capital. Trailing Stop protects profits.**
> Never mix stop-loss decisions with emotions.

---

## 2. Initial Stop Loss (Entry Protection)

### A. ATR-Based Stop Loss (Most Reliable)

**Applicable to all markets and timeframes**

**Formula:**

```
Initial SL = Entry Price − (ATR Multiplier × ATR)
```

**Recommended Multipliers:**

| Trading Style | ATR Multiplier |
| ------------- | -------------- |
| Scalping      | 1.2 × ATR      |
| Intraday      | 1.5 × ATR      |
| Swing         | 2.0 × ATR      |

**Use when:**

* Intraday trading
* Options trading
* High volatility instruments

---

### B. Structure-Based Stop Loss (High Accuracy)

Best suited for **price action trades**.

| Trade Type | Stop Loss Placement     |
| ---------- | ----------------------- |
| CALL       | Below recent Higher Low |
| PUT        | Above recent Lower High |

**Best Practice:**

```
Final SL = max(Structure SL, ATR SL)
```

---

## 3. Trailing Stop Loss Strategies (Profit Maximization)

### A. ATR Trailing Stop (Best Overall)

**Formula:**

```
Trailing SL = Highest Price − (1.3 × ATR)
```

**ATR Adjustment:**

| Market Condition | ATR Multiplier |
| ---------------- | -------------- |
| Strong Trend     | 1.3 × ATR      |
| Weak / Choppy    | 1.0 × ATR      |

**Advantages:**

* Automatically adapts to volatility
* Prevents premature exits
* Ideal for trending markets

---

### B. Step Trailing Stop (Options Friendly)

| Profit Level Achieved | Action                       |
| --------------------- | ---------------------------- |
| +1R                   | Move SL to Entry (Risk-Free) |
| +2R                   | Trail SL to +0.5R            |
| +3R                   | Trail SL to +1.5R            |

**Purpose:** Locks profits progressively and avoids full reversals.

---

### C. EMA-Based Trailing Stop (Trend Riding)

| Trade Type | Trailing Method      |
| ---------- | -------------------- |
| CALL       | SL below 20 / 21 EMA |
| PUT        | SL above 20 / 21 EMA |

Best used during strong directional trends.

---

## 4. Advanced Combo Strategy (High Expectancy Model)

### Entry Conditions

* RSI > 50 for CALL / RSI < 50 for PUT
* Clear market structure (Higher Highs / Lower Lows)

### Stop Loss Logic

```
Initial SL = max(Structure SL, 1.5 × ATR)
```

### Trailing Logic

```
If Profit ≥ 1.5R → SL = Entry
If Profit ≥ 2.5R → Trail using 1.2 × ATR
If Reversal Candle Appears → Exit 50% Position
```

**Benefit:** Improves expectancy while maintaining win rate.

---

## 5. Option-Specific Stop Loss & Trailing Logic

Options require **tighter risk control** due to theta decay, IV changes, and rapid price movement. The following rules are optimized for **index & stock options**.

---

### A. Option Initial Stop Loss (Premium-Based)

#### 1. ATR on Underlying (Preferred)

Use the **underlying chart**, not the option chart.

```
Underlying SL = 1.2 × ATR (Index Options)
Underlying SL = 1.5 × ATR (Stock Options)
```

Convert to option SL:

```
Option SL ≈ Option Delta × Underlying SL
```

---

#### 2. Fixed % Premium SL (Backup Rule)

Use only when ATR data is unreliable.

| Option Type   | Stop Loss         |
| ------------- | ----------------- |
| Index Options | 25–30% of premium |
| Stock Options | 30–35% of premium |

---

### B. Option Trailing Stop Loss (Best Practices)

#### 1. Step Trailing (Highly Effective for Options)

| Profit on Premium | Action           |
| ----------------- | ---------------- |
| +20–25%           | Move SL to Entry |
| +40–50%           | Lock +15–20%     |
| +70–80%           | Trail to +40–50% |

Purpose: Protects gains from sudden reversals.

---

#### 2. ATR Trailing on Underlying

```
Trailing SL (Underlying) = Highest Price − (1.0 × ATR)
Option SL = Delta × Underlying Trailing SL
```

Best used in trending index options.

---

#### 3. Time-Based Exit (Theta Protection)

| Time Condition | Exit Rule                            |
| -------------- | ------------------------------------ |
| Intraday       | Exit all options before last 30 mins |
| Weekly Expiry  | Avoid holding after Thursday noon    |
| Low Momentum   | Exit if no move within 3 candles     |

---

### C. Reversal & IV-Based Exit Rules

Exit option trades immediately if:

* Strong reversal candle on underlying
* RSI divergence against position
* Sudden IV crush near events
* Market structure break

---

### D. Recommended Option SL + Trailing Combo (One Rule)

```
Initial SL = 25% Premium OR (Delta × 1.2 ATR)
At +25% → SL = Entry
At +50% → Trail SL to +20%
At +75% → Trail SL to 1 × ATR (Underlying)
Hard Exit = Structure Break / Time Rule
```

---

## 6. What to Avoid (Common Loss Triggers)

* Fixed ₹ stop loss without premium logic
* Wide stop loss in options
* Ignoring delta & theta
* Holding losing options hoping for reversal

---

## 6. Recommended Universal Setup (One-Rule System)

```
Initial SL = 1.5 × ATR
Trail Activation = 1.8R
Trailing SL = 1.2 × ATR
Hard Exit = Market Structure Break
```

---

## 7. Next Steps (Automation Ready)

This strategy can be converted into:

* Pseudo-code for algorithmic trading
* Zerodha Kite API automation
* Backtesting modules
* Indicator-based strategy documents

---

*End of Document*
