# Simplified Implementation Roadmap

**Version**: 2.0 (Streamlined)
**Created**: January 31, 2026
**Goal**: Working paper trading bot in 3-4 weeks

---

## 🎯 Overview

This is a **streamlined, actionable roadmap** that focuses on the critical path to a working trading bot.

**Key Changes from Original Roadmap**:
- Removed non-essential features for MVP
- Consolidated phases for faster iteration
- Added practical "how-to" guidance for each step
- Focused on paper trading readiness, not perfection

---

## Week 1: Foundation (Config, Contracts, IBKR Client)

### Day 1-2: Configuration & Contracts
**Goal**: Load config, create MES contract
**Effort**: 6-9 hours total

#### bot/config.py (4-6 hours)
```python
# What to build:
from dataclasses import dataclass
from pathlib import Path
import yaml
import os

@dataclass
class StrategyConfig:
    lookback_period: int
    z_threshold_entry: float
    z_threshold_exit: float
    min_volume: int

@dataclass
class RiskConfig:
    max_position_size: int
    stop_loss_dollars: float
    take_profit_dollars: float
    max_daily_loss: float
    max_consecutive_losses: int
    max_position_duration_hours: float

@dataclass
class IBKRConfig:
    host: str
    port: int
    client_id: int
    account: str
    paper: bool

@dataclass
class Config:
    strategy: StrategyConfig
    risk: RiskConfig
    ibkr: IBKRConfig
    # ... other configs

def load_config(path: str) -> Config:
    """Load and validate configuration from YAML"""
    with open(path) as f:
        raw = yaml.safe_load(f)

    # Substitute environment variables
    def substitute_env(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.environ.get(var_name, value)
        return value

    # ... build Config object with validation
    return config
```

**Acceptance Criteria**:
- Loads `config/config.yaml.example`
- Substitutes `${TELEGRAM_BOT_TOKEN}`
- Validates all fields
- 10+ unit tests pass

---

#### bot/ibkr/contracts.py (2-3 hours)
```python
# What to build:
from ib_async import Contract

def create_mes_contract(expiry: str) -> Contract:
    """Create MES futures contract

    Args:
        expiry: YYYYMM format (e.g., "202503")

    Returns:
        ib_async Contract object
    """
    contract = Contract(
        symbol="MES",
        secType="FUT",
        exchange="CME",
        currency="USD",
        lastTradeDateOrContractMonth=expiry
    )
    return contract
```

**Acceptance Criteria**:
- Creates valid MES contract
- Validates expiry format
- 5+ unit tests pass

---

### Day 3-5: IBKR Client (Hardest Module)
**Goal**: Connect to IBKR, receive data, place orders
**Effort**: 2-3 days (16-24 hours)

**Library Decision**: Use `ib_async` (not raw `ibapi`)
```bash
pip install ib_async
```

#### bot/ibkr/client.py - Phased Approach

**Phase A: Connection (4-6 hours)**
```python
from ib_async import IB, util
import asyncio

class IBKRClient:
    def __init__(self, host: str, port: int, client_id: int):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id

    async def connect(self):
        """Connect to IB Gateway"""
        await self.ib.connectAsync(self.host, self.port, self.client_id)

    async def disconnect(self):
        """Disconnect gracefully"""
        self.ib.disconnect()

    async def is_connected(self) -> bool:
        """Check connection status"""
        return self.ib.isConnected()
```

**Test**: Connect to IB Gateway, verify connection stays alive for 5 minutes

---

**Phase B: Market Data (4-6 hours)**
```python
async def subscribe_bars(self, contract, bar_size: str, callback):
    """Subscribe to real-time bars

    Args:
        contract: ib_async Contract
        bar_size: "5 mins", "1 min", etc.
        callback: Function to call with each bar
    """
    bars = await self.ib.reqRealTimeBarsAsync(
        contract=contract,
        barSize=5,  # seconds
        whatToShow="TRADES",
        useRTH=False  # Include after-hours
    )

    def on_bar_update(bars, has_new_bar):
        if has_new_bar:
            bar = bars[-1]
            callback(bar)

    bars.updateEvent += on_bar_update
    return bars
```

**Test**: Receive live MES bars, verify callback fires every 5 minutes

---

**Phase C: Order Execution (4-6 hours)**
```python
async def place_market_order(self, contract, action: str, quantity: int):
    """Place market order

    Args:
        contract: ib_async Contract
        action: "BUY" or "SELL"
        quantity: Number of contracts

    Returns:
        Trade object
    """
    from ib_async import MarketOrder

    order = MarketOrder(action, quantity)
    trade = self.ib.placeOrder(contract, order)

    # Wait for fill
    while not trade.isDone():
        await asyncio.sleep(0.1)

    return trade
```

**Test**: Place order in paper trading, verify fill

---

**Phase D: Position Tracking (2-3 hours)**
```python
async def get_positions(self):
    """Get all current positions"""
    return self.ib.positions()

async def flatten_all(self):
    """Emergency close all positions"""
    positions = await self.get_positions()
    for pos in positions:
        action = "SELL" if pos.position > 0 else "BUY"
        await self.place_market_order(
            pos.contract,
            action,
            abs(pos.position)
        )
```

**Test**: Open position, verify tracking, flatten successfully

---

**Acceptance Criteria (Full IBKR Client)**:
- Connects and stays connected
- Receives real-time 5-minute bars
- Places market orders successfully
- Tracks positions accurately
- Flattens positions on command
- Handles disconnection and reconnects
- 15+ integration tests pass

---

## Week 2: Trading Logic (Signals, Risk, Database)

### Day 6: Signal Generation
**Goal**: Convert bars → trading signals
**Effort**: 6-8 hours

#### bot/core/signals.py
```python
from enum import Enum
from dataclasses import dataclass
from quant_scalper_rust import ZScoreEngine

class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    NONE = "NONE"

@dataclass
class Signal:
    signal_type: SignalType
    timestamp: datetime
    price: float
    z_score: float
    volume: int

class SignalGenerator:
    def __init__(self, config):
        self.config = config
        self.z_engine = ZScoreEngine(config.strategy.lookback_period)
        self.current_position = None  # "LONG", "SHORT", or None

    def on_bar(self, bar) -> Optional[Signal]:
        """Process bar and generate signal"""

        # Update Z-Score
        z_score = self.z_engine.update(bar.close)
        if z_score is None:
            return None  # Warming up

        # Check volume filter
        if bar.volume < self.config.strategy.min_volume:
            return None

        # Generate signal based on state and Z-Score
        if self.current_position is None:
            # Look for entry
            if z_score >= self.config.strategy.z_threshold_entry:
                return Signal(SignalType.SHORT, bar.time, bar.close, z_score, bar.volume)
            elif z_score <= -self.config.strategy.z_threshold_entry:
                return Signal(SignalType.LONG, bar.time, bar.close, z_score, bar.volume)

        elif self.current_position == "LONG":
            # Look for exit
            if abs(z_score) <= self.config.strategy.z_threshold_exit:
                return Signal(SignalType.EXIT_LONG, bar.time, bar.close, z_score, bar.volume)

        elif self.current_position == "SHORT":
            # Look for exit
            if abs(z_score) <= self.config.strategy.z_threshold_exit:
                return Signal(SignalType.EXIT_SHORT, bar.time, bar.close, z_score, bar.volume)

        return None
```

**Acceptance Criteria**:
- Generates LONG when Z <= -2.0
- Generates SHORT when Z >= +2.0
- Generates EXIT when Z returns to ±0.5
- Respects volume filter
- 20+ unit tests with mock bars

---

### Day 7: Circuit Breaker
**Goal**: Enforce risk limits
**Effort**: 6-8 hours

#### bot/risk/circuit_breaker.py
```python
from datetime import datetime, timedelta, timezone

class CircuitBreaker:
    def __init__(self, config):
        self.config = config
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trade_count_today = 0
        self.paused_until: Optional[datetime] = None
        self.position_entry_time: Optional[datetime] = None

    def check_can_trade(self) -> tuple[bool, Optional[str]]:
        """Check if trading is allowed

        Returns:
            (can_trade, reason_if_not)
        """

        # Check if paused
        if self.paused_until and datetime.now(timezone.utc) < self.paused_until:
            return False, f"Paused until {self.paused_until}"

        # Check daily loss limit
        if self.daily_pnl <= -self.config.risk.max_daily_loss:
            return False, f"Daily loss limit: ${abs(self.daily_pnl):.2f}"

        # Check max trades
        if self.trade_count_today >= 50:  # Add to config
            return False, f"Max trades/day: {self.trade_count_today}"

        return True, None

    def record_trade(self, pnl: float):
        """Record trade and update state"""
        self.daily_pnl += pnl
        self.trade_count_today += 1

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Trigger pause if needed
        if self.consecutive_losses >= self.config.risk.max_consecutive_losses:
            self.paused_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    def check_position_duration(self) -> bool:
        """Check if position held too long"""
        if not self.position_entry_time:
            return False

        duration_hours = (datetime.now(timezone.utc) - self.position_entry_time).total_seconds() / 3600
        return duration_hours >= self.config.risk.max_position_duration_hours

    def reset_daily(self):
        """Reset daily counters (call at market open)"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trade_count_today = 0
```

**Acceptance Criteria**:
- Blocks trading when daily loss >= $500
- Pauses for 30 min after 3 consecutive losses
- Blocks after max trades/day
- 10+ unit tests

---

### Day 8: Database (Optional for MVP)
**Goal**: Log trades and events
**Effort**: 4-6 hours

**MVP Alternative**: Skip database, use structured file logging initially

#### bot/persistence/database.py (If implementing)
```python
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    realized_pnl = Column(Float, default=0.0)
    z_score = Column(Float)

class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def log_trade(self, trade_data):
        trade = Trade(**trade_data)
        self.session.add(trade)
        self.session.commit()
```

**Acceptance Criteria**:
- Creates SQLite database
- Logs trades successfully
- Query functions work
- 8+ unit tests

---

## Week 3: Integration (Engine + Main)

### Day 9-10: Trading Engine
**Goal**: Orchestrate all components
**Effort**: 12-16 hours

#### bot/core/engine.py
```python
from enum import Enum

class EngineState(Enum):
    IDLE = "IDLE"
    ENTERING_LONG = "ENTERING_LONG"
    LONG = "LONG"
    EXITING_LONG = "EXITING_LONG"
    ENTERING_SHORT = "ENTERING_SHORT"
    SHORT = "SHORT"
    EXITING_SHORT = "EXITING_SHORT"

class TradingEngine:
    def __init__(self, config):
        self.config = config
        self.ibkr = IBKRClient(config.ibkr.host, config.ibkr.port, config.ibkr.client_id)
        self.signal_gen = SignalGenerator(config)
        self.circuit_breaker = CircuitBreaker(config)
        self.telegram = TelegramAlertManager(config.alerts.telegram)
        self.state = EngineState.IDLE
        self.current_position = None

    async def start(self):
        """Start the trading engine"""
        # Connect to IBKR
        await self.ibkr.connect()

        # Start Telegram
        await self.telegram.start()

        # Subscribe to market data
        contract = create_mes_contract(self.config.instruments[0].expiry)
        await self.ibkr.subscribe_bars(contract, "5 mins", self.on_bar)

        # Send startup alert
        await self.telegram.send_startup("PAPER", "MES", self.config.risk.max_daily_loss)

        # Keep running
        while True:
            await asyncio.sleep(1)

            # Check position duration
            if self.state in [EngineState.LONG, EngineState.SHORT]:
                if self.circuit_breaker.check_position_duration():
                    await self.force_exit()

    async def on_bar(self, bar):
        """Handle incoming bar data"""
        # Generate signal
        signal = self.signal_gen.on_bar(bar)

        if signal:
            await self.process_signal(signal)

    async def process_signal(self, signal):
        """Process a trading signal"""
        # Check circuit breaker
        can_trade, reason = self.circuit_breaker.check_can_trade()
        if not can_trade:
            await self.telegram.send_error(f"Signal blocked: {reason}")
            return

        # Check trading hours
        if not is_trading_allowed(config=self.config):
            return

        # Execute based on signal and state
        if signal.signal_type == SignalType.LONG and self.state == EngineState.IDLE:
            await self.enter_long(signal)
        elif signal.signal_type == SignalType.SHORT and self.state == EngineState.IDLE:
            await self.enter_short(signal)
        elif signal.signal_type == SignalType.EXIT_LONG and self.state == EngineState.LONG:
            await self.exit_long(signal)
        elif signal.signal_type == SignalType.EXIT_SHORT and self.state == EngineState.SHORT:
            await self.exit_short(signal)

    async def enter_long(self, signal):
        """Enter long position"""
        contract = create_mes_contract(self.config.instruments[0].expiry)
        quantity = self.config.risk.max_position_size

        trade = await self.ibkr.place_market_order(contract, "BUY", quantity)
        self.state = EngineState.LONG
        self.circuit_breaker.position_entry_time = datetime.now(timezone.utc)
        self.signal_gen.update_position("LONG")

        await self.telegram.send_trade_entry(
            "LONG", "MES", quantity, signal.price, signal.z_score, "Z-Score <= -2.0"
        )

    # ... implement enter_short, exit_long, exit_short similarly

    async def shutdown(self):
        """Graceful shutdown"""
        await self.ibkr.flatten_all()
        await self.ibkr.disconnect()
        await self.telegram.stop()
```

**Acceptance Criteria**:
- Connects to IBKR successfully
- Receives bars and generates signals
- Executes orders based on signals
- Respects circuit breaker
- Handles graceful shutdown
- Integration test with live data (paper account)

---

### Day 11: Main Entry Point
**Goal**: Bootstrap the application
**Effort**: 2-3 hours

#### bot/main.py
```python
import asyncio
import argparse
import logging
import sys

from bot.config import load_config
from bot.core.engine import TradingEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

async def main():
    parser = argparse.ArgumentParser(description="Quant Scalper Trading Bot")
    parser.add_argument("config", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Create engine
    engine = TradingEngine(config)

    # Start
    await engine.start()

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria**:
- Loads config from command line
- Starts trading engine
- Handles SIGTERM/SIGINT
- Logs to file and console

---

## Week 4: Testing & Validation

### Testing Checklist

#### Unit Tests (Day 12-13)
- [ ] bot/config.py (15 tests)
- [ ] bot/core/signals.py (20 tests)
- [ ] bot/risk/circuit_breaker.py (10 tests)
- [ ] bot/ibkr/contracts.py (5 tests)
- [ ] Target: >80% code coverage

#### Integration Tests (Day 14)
- [ ] IBKR client connection
- [ ] Market data flow
- [ ] Order execution
- [ ] Full signal → order flow

#### System Test (Day 15-18)
- [ ] 48+ hour continuous run
- [ ] Monitor memory usage
- [ ] Test crash recovery
- [ ] Test IB Gateway disconnect
- [ ] Review all logs

#### Edge Cases (Day 19)
- [ ] Market close handling
- [ ] Order rejection
- [ ] Extreme Z-Scores
- [ ] Connection loss during order

---

## Success Criteria (Paper Trading Ready)

### Technical
- [x] All modules implemented
- [ ] All tests passing (>80% coverage)
- [ ] 48+ hours continuous operation
- [ ] No crashes or hangs
- [ ] Graceful handling of disconnects

### Functional
- [ ] Generates correct signals
- [ ] Places orders successfully
- [ ] Circuit breaker works
- [ ] Position tracking accurate
- [ ] Telegram alerts delivered

### Operational
- [ ] Emergency flatten tested
- [ ] Startup/shutdown clean
- [ ] Logs are clear and useful
- [ ] Can recover from crashes

---

## What We're NOT Building (Yet)

To keep scope manageable, explicitly defer:

- ❌ Web dashboard
- ❌ Backtest engine
- ❌ Telegram command handler
- ❌ Multiple instruments
- ❌ Multiple timeframes
- ❌ ML parameter optimization
- ❌ Trend filter
- ❌ Trailing stops

These can be added AFTER successful paper trading.

---

## Daily Standup Questions

Ask yourself each day:
1. What did I complete yesterday?
2. What am I working on today?
3. What's blocking me?
4. Am I on track for the weekly goal?

---

**Remember**: The goal is a WORKING paper trading bot, not a perfect one. Ship first, iterate later.
