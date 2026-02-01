# Research Summary - Quant Scalping Bot

**Researched:** 2026-01-31

---

## 1. ib_async vs Raw ibapi

### What is ib_async?
`ib_async` is an async Python wrapper around Interactive Brokers TWS API (ibapi) that provides:
- **Native async/await support** — Modern Python async patterns
- **Cleaner error handling** — Better exception handling and reconnection logic
- **Event-driven architecture** — Natural fit for trading systems
- **Simpler code** — Less boilerplate than raw ibapi

### Key Advantages

| Feature | Raw ibapi | ib_async |
|----------|-------------|-----------|
| Async/Await | ❌ Requires custom threading | ✅ Native support |
| Connection Management | Manual reconnect | ✅ Built-in auto-reconnect |
| Order Management | Complex callback handling | ✅ Coroutine-based |
| Error Handling | Manual try-catch everywhere | ✅ Centralized handling |
| Code Readability | Callback hell | ✅ Clean async code |

### Why Opus Recommends ib_async

Based on the bot's architecture (async components everywhere - Telegram, database, risk management), `ib_async` fits naturally:

**Current Stack:**
- Telegram alerts: `asyncio` ✅
- Database: SQLite (sync) → needs SQLAlchemy async later ✅
- Risk management: Need async for real-time checks ✅

**Raw ibapi Problem:** Mixing synchronous IB callbacks with async code creates threading complexity.

**ib_async Solution:** Everything is async, consistent architecture.

---

## 2. CME Futures Trading Hours

### MES (Micro E-mini S&P 500) Trading Hours

**NOT 9:30 AM - 4:00 PM (that's stocks!)**

**Actual Futures Hours:**
- **Sunday-Friday:** 5:00 PM CT (previous day) → 4:00 PM CT (current day)
- **Weekly:** 5:00 PM Sunday CT → 4:00 PM Friday CT
- **Daily:** 5:00 PM CT (Sunday) → 4:00 PM CT (Monday-Friday)
- **Break:** 4:00 PM CT → 5:00 PM CT (daily maintenance)

### In GMT+8 (Singapore Time)
- Open: 7:00 AM (next day)
- Close: 6:00 AM (next day)
- Actually trades: ~23 hours/day

### What the Current Code Does Wrong
```python
# bot/utils/timezone.py (line 216) - WRONG
is_trading_allowed():
    return 9:30 < current_time < 16:00  # Stock hours!
```

**Result:** Bot only trades 6.5 hours/day instead of 23 hours = **75% of opportunities missed**

### Fix Required
```python
def is_futures_trading_hours(dt: datetime) -> bool:
    """Check if datetime is within CME futures trading hours"""
    day_of_week = dt.weekday()  # 0=Mon, 6=Sun
    
    # Sunday night to Friday afternoon
    if day_of_week == 6:  # Saturday
        return False
    if day_of_week == 5:  # Friday
        return dt.hour < 16  # Close 4pm CT
    
    # Sunday 5pm CT = Monday 7am GMT+8
    if day_of_week == 0:  # Sunday
        return dt.hour >= 7  # Open 7am GMT+8
    
    # Mon-Thu: All day
    return True
```

---

## 3. MES Contract Specifications

### Current Price: ~6,965.75 USD (Jan 2026)

### Contract Details
| Spec | Value |
|-------|-------|
| Symbol | MES (Micro E-mini S&P 500) |
| Underlying | S&P 500 Index |
| Multiplier | $5 per index point |
| Tick Size | 0.25 index points = $1.25 |
| Minimum Tick | $1.25 |
| Contract Size | $5 × index value |
| Contract Months | Quarterly (H, M, U, Z) |
| Trading Hours | ~23 hours/day (see above) |
| Exchange | CME Group (Chicago) |

### Margin Requirements (Approximate, varies)
- **Intraday margin:** ~$1,500 - $2,000
- **Overnight margin:** ~$3,000 - $5,000
- **Full contract value:** $5 × 6,965 = ~$34,800

### Point Value Calculations
```
1 point change = $5 P&L
0.25 tick change = $1.25 P&L
40 points = $200 P&L  (Stop Loss)
60 points = $300 P&L  (Take Profit)
```

### Why This Matters
The bot's current parameters ($200 SL, $300 TP) = 40-60 points = **swing trading**, not scalping.

**True Scalping:**
- 2-10 points = $10-$50 targets
- Ticker-tape execution
- Hold times: seconds to minutes

**Current Strategy:**
- 40-60 points = swing trading levels
- Hold times: hours
- More like day trading than scalping

---

## 4. Numerical Stability for Z-Score (Welford's Algorithm)

### The Problem with Current Rust Code

```rust
// rust/src/zscore.rs - NUMERICALLY UNSTABLE!
pub fn update(&mut self, price: f64) -> Option<f64> {
    self.sum += price;
    self.sum_sq += price * price;
    // Then: variance = (sum_sq - (sum * sum) / n) / (n - 1)
    // ^^^ CATASTROPHIC CANCELLATION with large values
}
```

**Why It's Bad:**
- MES price ~6,000
- 20 bars: sum ≈ 120,000, sum_sq ≈ 720,000,000
- `sum_sq - (sum * sum) / n` = huge minus huge = precision loss
- Over time: floating-point errors accumulate
- **Result:** Z-Score drifts from true value → wrong signals

### The Fix: Welford's Online Algorithm

```rust
// Numerically stable variance calculation
pub struct ZScoreEngine {
    mean: f64,
    m2: f64,        // Sum of squared deviations from mean
    count: usize,
}

impl ZScoreEngine {
    pub fn update(&mut self, x: f64) -> Option<f64> {
        self.count += 1;
        
        // Welford's algorithm: incremental mean update
        let delta = x - self.mean;
        self.mean += delta / self.count as f64;
        let delta2 = x - self.mean;
        
        // Incrementally update M2 (sum of squared deviations)
        self.m2 += delta * delta2;
        
        // Calculate variance from M2 (no cancellation!)
        let variance = if self.count > 1 {
            self.m2 / (self.count - 1) as f64
        } else {
            0.0
        };
        
        let std_dev = variance.sqrt();
        Some((x - self.mean) / std_dev)
    }
}
```

**Why It Works:**
- Never calculates `sum_sq - (sum * sum) / n` (the problematic part)
- Updates mean incrementally, tracking deviation from current mean
- Numerically stable for any price values
- Same complexity, better precision

---

## 5. ADX Trend Filter for Mean Reversion

### What is ADX?

**ADX = Average Directional Index**
- Measures trend strength (0-100)
- Includes +DI (uptrend), -DI (downtrend)
- Created by Welles Wilder for commodities

### How ADX Prevents Mean Reversion Errors

Mean reversion assumes price returns to mean. But in **strong trends**, it doesn't!

**Problem:** Price trending up → mean keeps rising → Z-Score says "oversold" → bot buys WRONG

**ADX Solution:**
```
If ADX > 25: TRENDING
    → DON'T trade mean reversion
    → Or use trend-following strategy
    
If ADX < 20: RANGING / TRENDLESS
    → OK to use mean reversion
    → Z-Score signals are valid
```

### Implementation Example

```python
class ADXFilter:
    def __init__(self, period: int = 14):
        self.period = period
        self.highs = deque(maxlen=period)
        self.lows = deque(maxlen=period)
        self.adx = 0.0
    
    def update(self, high: float, low: float) -> bool:
        self.highs.append(high)
        self.lows.append(low)
        
        # Calculate +DM, -DM, TR (simplified)
        # ... (full calculation requires multiple steps)
        
        # Update ADX using Wilder's smoothing
        # ADX = ((prior_ADX * 13) + current_DX) / 14
        
        return self.adx < 20  # True = tradeable
    
    def should_skip_trade(self) -> bool:
        return self.adx > 25  # True = trending, skip
```

### Recommended ADX Parameters for MES

| Setting | Value | Reason |
|----------|---------|---------|
| Period | 14 | Standard for commodities (Wilder's recommendation) |
| Trend Threshold | 25 | Strong trend (don't trade mean reversion) |
| Range Threshold | 20 | Weak trend (OK to trade) |
| Warmup Period | 14 bars | Need 14 periods for valid ADX |

---

## 6. CME Holidays 2026

### Key CME Holidays 2026

Based on CME Group holiday schedule:

| Holiday | Date | Trading |
|---------|--------|----------|
| New Year's Day | January 1, 2026 | CLOSED |
| MLK Day | January 19, 2026 | **CLOSED 8:30am-1pm** |
| Presidents' Day | February 16, 2026 | **CLOSED 8:30am-1pm** |
| Good Friday | April 3, 2026 | **CLOSED 8:30am-1pm** |
| Memorial Day | May 25, 2026 | **CLOSED 8:30am-1pm** |
| Juneteenth | June 19, 2026 | **CLOSED 8:30am-1pm** |
| Independence Day | July 3, 2026 (observed) | **CLOSED 8:30am-1pm** |
| Labor Day | September 7, 2026 | **CLOSED 8:30am-1pm** |
| Thanksgiving | November 26, 2026 | **CLOSED 8:30am-1pm** |
| Day after Thanksgiving | November 27, 2026 | **CLOSED 8:30am-1pm** |
| Christmas | December 25, 2026 | CLOSED |

### Notes:
- **"Early Close"** = 8:30 AM - 1:00 PM CT
- **Full Close** = No trading
- Current code has only 2025 holidays — needs update to 2026

---

## 7. Scalping vs Swing Trading Parameters

### The Bot's Current Parameters

| Parameter | Value | Points | P&L | Classification |
|------------|----------|---------|----------------|
| Stop Loss | $200 | 40 points | **Swing** |
| Take Profit | $300 | 60 points | **Swing** |
| Hold Time | 2 hours | - | **Swing** |

### True Scalping Parameters

| Parameter | Value | Points | P&L | Classification |
|------------|----------|---------|----------------|
| Stop Loss | $20-50 | 4-10 points | **Scalping** |
| Take Profit | $30-75 | 6-15 points | **Scalping** |
| Hold Time | 5-30 minutes | - | **Scalping** |
| Execution | Tape reading | - | **Scalping** |

### Which Should We Use?

**Option A: True Scalping** (as project name suggests)
- Pros: Many small wins, reduced overnight risk
- Cons: Requires execution excellence, high commission ratio
- Recommended if: You can be at screen during market hours

**Option B: Swing/Day Trading** (as current parameters suggest)
- Pros: Fewer trades, less screen time
- Cons: Larger drawdowns per trade
- Recommended if: You have full-time job, can't monitor constantly

### Recommendation for Your Situation

Given:
- Fire Furnace energy (high intensity)
- Want passive income (bot runs 24/7)
- Bazi suggests Earth products (tangible, stable)

**Recommendation:** Stick with current **swing/day trading** parameters but **rename project**:
- `quant-swinger` or `day-trader-bot`
- Adjust expectations: Not scalping, it's mean reversion day trading
- Or: If you want true scalping, reduce targets to 4-10 points

---

## 8. Trump's X (Twitter) News Indicator

### Concept

Track Trump's tweets/posts on X (formerly Twitter) for market-moving events:

- **Trade policy announcements** → Market reacts instantly
- **China tariffs** → Affects global markets, futures volatility
- **Fed criticism** → Interest rate expectations shift
- **Election news** → Major market moves

### Implementation Approach

**Method A: X API (Official)**
- Apply for X Developer Access
- Monitor @realDonaldTrump account
- Parse tweets for keywords: "tariff", "China", "Fed", "trade", "tax"

```python
class TrumpNewsIndicator:
    def __init__(self, api_key: str):
        self.client = tweepy.Client(api_key)
        self.keywords = ["tariff", "China", "Fed", "trade", "tax"]
    
    async def monitor(self):
        async for tweet in self.client.get_users_tweets(id="realDonaldTrump"):
            if self.contains_trading_keyword(tweet.text):
                self.trigger_market_alert(tweet)
```

**Method B: Third-Party Services**
- Bloomberg Terminal News API
- Refinitiv News Feed
- Custom sentiment analysis via NLP

### Risk: Volatility Spikes

**What Happens When Trump Tweets:**

```
Trump tweet: "I'll impose 50% tariff on China"
→ Market reaction: -2% in 1 minute
→ Mean reversion bot: Sees "oversold", buys WRONG
→ Bot gets crushed by continued drop
```

**Solution: Pause Trading During News**

```python
def should_pause_trading() -> bool:
    # Check if Trump tweeted in last 15 minutes
    if trump_news.minutes_since_last() < 15:
        return True  # PAUSE trading
    
    # Check ADX (trend filter)
    if adx_filter.should_skip_trade():
        return True  # PAUSE trading
    
    return False  # OK to trade
```

### Recommended Implementation

**Phase 1 (POC):**
- Manual Twitter monitoring
- Manual pause button in Telegram: `/pause 60` (pause for 60 minutes)
- Review Trump's account manually during market hours

**Phase 2 (Automated):**
- X API integration
- Keyword detection
- Auto-pause trading for 15-30 minutes after significant tweets

**Phase 3 (Advanced):**
- Sentiment analysis (positive/negative)
- Combine with ADX filter
- Dynamic position sizing based on volatility

---

## 📊 Summary: Priority Fixes

| Issue | Fix Complexity | Impact |
|-------|----------------|----------|
| Z-Score numerical stability | MEDIUM (Rust code change) | Critical - wrong signals |
| Trading hours (stock vs futures) | LOW (timezone.py fix) | High - 75% opportunities missed |
| Holiday calendar 2026 | LOW (add dates) | Medium - trading on closed days |
| Telegram HTML injection | LOW (sanitization) | Medium - security issue |

---

## 💡 Recommendations Summary

1. **Use ib_async** — Clean async architecture, better error handling
2. **Fix Z-Score with Welford's algorithm** — Numerically stable
3. **Update to CME futures hours** — 23 hours/day vs 6.5 hours
4. **Add ADX filter** — Don't mean-revert during trends
5. **Decide: Scalping or Swing?** — Rename project or adjust parameters
6. **Add Trump news filter** — Pause trading during volatility spikes
7. **Update holiday calendar** — Add 2026 CME holidays
8. **Define bar timeframe** — 1-minute? 5-minute? "20 bars" is meaningless

---

**Next:** Which should we tackle first? Z-Score fix is most critical (wrong signals = losing money).
