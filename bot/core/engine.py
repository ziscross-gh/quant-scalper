"""
Trading Engine

Main trading logic: manages state, signals, orders, and risk.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from ..config import Config

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Current position state"""
    quantity: int = 0  # Positive = LONG, Negative = SHORT, 0 = Flat
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    entry_zscore: float = 0.0


@dataclass
class DailyStats:
    """Daily trading statistics"""
    start_date: datetime = field(default_factory=datetime.utcnow)
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    consecutive_losses: int = 0
    realized_pnl: float = 0.0


@dataclass
class EngineState:
    """Complete engine state"""
    position: Position = field(default_factory=Position)
    daily_stats: DailyStats = field(default_factory=DailyStats)
    current_zscore: Optional[float] = None
    is_running: bool = True
    is_paused: bool = False
    circuit_breaker_triggered: bool = False


# Dummy alert manager for when alerts are disabled
class DummyAlertManager:
    """No-op alert manager"""
    async def start(self): pass
    async def stop(self): pass
    async def send_startup(self, mode, instrument, max_loss): pass
    async def send_connected(self): pass
    async def send_disconnected(self): pass
    async def send_trade_entry(self, direction, symbol, quantity, price, zscore, reason): pass
    async def send_trade_exit(self, symbol, exit_price, pnl, zscore): pass
    async def send_circuit_breaker(self, reason): pass
    async def send_daily_summary(self, net_pnl, trades_count, win_rate, winning, losing, profit_factor): pass
    async def send_error(self, error): pass
    async def send_shutdown(self, reason): pass
    async def send_status(self, state, position, daily_pnl, unrealized_pnl, zscore): pass


class TradingEngine:
    """Main trading engine"""

    def __init__(self, config: Config, alerts: Optional[Any] = None):
        self.config = config
        self.alerts = alerts or DummyAlertManager()
        self.signal_gen = SignalGenerator(config.strategy.lookback_period)

        self.state = EngineState()
        self._shutdown_event = asyncio.Event()

        # Will be set when IBKR client connects
        self.ibkr_client = None

    def set_ibkr_client(self, client):
        """Set the IBKR client for order execution"""
        self.ibkr_client = client
        logger.info("IBKR client connected to engine")

    async def start(self):
        """Start the trading engine"""
        logger.info("Starting trading engine")

        # Send startup notification
        instrument = self.config.instruments[0].symbol
        await self.alerts.send_startup(
            mode="paper" if self.config.ibkr.paper else "live",
            instrument=instrument,
            max_loss=self.config.risk.max_daily_loss,
        )

        # Initialize signal generator
        logger.info(f"Signal generator initialized with lookback={self.config.strategy.lookback_period}")

    async def stop(self, reason: str = "Manual"):
        """Stop the trading engine"""
        logger.info(f"Stopping trading engine: {reason}")

        self.state.is_running = False
        self._shutdown_event.set()

        # Send shutdown notification
        await self.alerts.send_shutdown(reason)

    async def process_bar(self, bar: Dict[str, Any]):
        """Process a new market data bar"""
        if not self.state.is_running or self.state.is_paused:
            return

        try:
            # Check trading hours first (CME futures hours)
            from ..utils.timezone import is_trading_allowed

            if not is_trading_allowed():
                # Market closed or maintenance window
                logger.debug("Market closed - not processing signals")
                return

            # Update Z-Score
            price = bar.get("close", bar.get("midPrice", 0))
            self.state.current_zscore = self.signal_gen.update(price)

            if not self.signal_gen.is_ready():
                logger.debug("Signal generator warming up...")
                return

            # Generate and handle signal
            signal = self.signal_gen.get_signal()

            if signal:
                await self._handle_signal(signal)

        except Exception as e:
            logger.exception(f"Error processing bar: {e}")
            await self.alerts.send_error(f"Process bar error: {str(e)}")

    async def _handle_signal(self, signal: Dict[str, Any]):
        """Handle a trading signal"""
        if not self.ibkr_client:
            logger.warning("No IBKR client connected, ignoring signal")
            return

        signal_type = signal["type"]
        zscore = self.state.current_zscore

        logger.info(f"Signal: {signal_type} (Z={zscore:.2f})")

        # Check circuit breakers
        if self.state.circuit_breaker_triggered:
            logger.info("Circuit breaker active, ignoring signals")
            return

        # Handle signal
        if signal_type == "ENTER_LONG":
            await self._enter_long(zscore)
        elif signal_type == "ENTER_SHORT":
            await self._enter_short(zscore)
        elif signal_type == "EXIT":
            await self._exit_position(signal.get("reason", "Z-Score reversion"))

    async def _enter_long(self, zscore: float):
        """Enter a long position"""
        if self.state.position.quantity > 0:
            logger.debug("Already long, ignoring ENTER_LONG signal")
            return

        instrument = self.config.instruments[0]
        qty = 1  # Start with 1 contract

        logger.info(f"Entering LONG position: {qty} {instrument.symbol}")

        # Execute order (would use IBKR client here)
        if not self.config.debug.dry_run and self.ibkr_client:
            await self.ibkr_client.place_order(
                symbol=instrument.symbol,
                quantity=qty,
                action="BUY",
            )

        # Update state
        self.state.position.quantity = qty
        self.state.position.entry_time = datetime.utcnow()
        self.state.position.entry_zscore = zscore

        # Send alert
        await self.alerts.send_trade_entry(
            direction="LONG",
            symbol=instrument.symbol,
            quantity=qty,
            price=0.0,  # Would get actual fill price
            zscore=zscore,
            reason=f"Z-Score ≤ -{self.config.strategy.z_threshold_entry}",
        )

    async def _enter_short(self, zscore: float):
        """Enter a short position"""
        if self.state.position.quantity < 0:
            logger.debug("Already short, ignoring ENTER_SHORT signal")
            return

        instrument = self.config.instruments[0]
        qty = 1

        logger.info(f"Entering SHORT position: {qty} {instrument.symbol}")

        # Execute order
        if not self.config.debug.dry_run and self.ibkr_client:
            await self.ibkr_client.place_order(
                symbol=instrument.symbol,
                quantity=qty,
                action="SELL",
            )

        # Update state
        self.state.position.quantity = -qty
        self.state.position.entry_time = datetime.utcnow()
        self.state.position.entry_zscore = zscore

        # Send alert
        await self.alerts.send_trade_entry(
            direction="SHORT",
            symbol=instrument.symbol,
            quantity=qty,
            price=0.0,  # Would get actual fill price
            zscore=zscore,
            reason=f"Z-Score ≥ +{self.config.strategy.z_threshold_entry}",
        )

    async def _exit_position(self, reason: str):
        """Exit current position"""
        if self.state.position.quantity == 0:
            logger.debug("No position to exit")
            return

        instrument = self.config.instruments[0]
        qty = abs(self.state.position.quantity)
        action = "SELL" if self.state.position.quantity > 0 else "BUY"

        logger.info(f"Exiting position: {action} {qty} {instrument.symbol}")

        # Execute order
        if not self.config.debug.dry_run and self.ibkr_client:
            await self.ibkr_client.place_order(
                symbol=instrument.symbol,
                quantity=qty,
                action=action,
            )

        # Calculate P&L (would get from IBKR in real implementation)
        pnl = 0.0  # Placeholder

        # Update stats
        self.state.daily_stats.trades_count += 1
        if pnl >= 0:
            self.state.daily_stats.winning_trades += 1
            self.state.daily_stats.consecutive_losses = 0
        else:
            self.state.daily_stats.losing_trades += 1
            self.state.daily_stats.consecutive_losses += 1

        self.state.daily_stats.realized_pnl += pnl

        # Send alert
        await self.alerts.send_trade_exit(
            symbol=instrument.symbol,
            exit_price=0.0,  # Would get actual exit price
            pnl=pnl,
            zscore=self.state.current_zscore or 0.0,
        )

        # Reset position
        self.state.position = Position()

    async def check_risk_limits(self):
        """Check risk limits and trigger circuit breakers if needed"""
        stats = self.state.daily_stats

        # Check daily loss limit
        if stats.realized_pnl <= -self.config.risk.max_daily_loss:
            await self._trigger_circuit_breaker("daily_loss_limit")
            return

        # Check consecutive losses
        if stats.consecutive_losses >= self.config.risk.max_consecutive_losses:
            await self._trigger_circuit_breaker("consecutive_losses")
            return

        # Check position duration
        if self.state.position.entry_time:
            duration = datetime.utcnow() - self.state.position.entry_time
            max_duration = timedelta(hours=self.config.risk.max_position_duration_hours)
            if duration >= max_duration and self.state.position.quantity != 0:
                logger.warning("Position held too long, forcing exit")
                await self._exit_position("Position duration limit")
                await self._trigger_circuit_breaker("position_timeout")

    async def _trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker and halt trading"""
        logger.error(f"Circuit breaker triggered: {reason}")
        self.state.circuit_breaker_triggered = True
        self.state.is_paused = True

        # Flatten all positions
        if self.state.position.quantity != 0:
            await self._exit_position("Circuit breaker")

        # Send alert
        await self.alerts.send_circuit_breaker(reason)

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        return {
            "running": self.state.is_running,
            "paused": self.state.is_paused,
            "circuit_breaker": self.state.circuit_breaker_triggered,
            "position": self.state.position.quantity,
            "daily_pnl": self.state.daily_stats.realized_pnl,
            "trades_today": self.state.daily_stats.trades_count,
            "zscore": self.state.current_zscore,
        }

    async def send_status_update(self):
        """Send current status to Telegram"""
        status = self.get_status()
        state = "stopped" if not self.state.is_running else \
                "paused" if self.state.is_paused else "running"

        await self.alerts.send_status(
            state=state,
            position=status["position"],
            daily_pnl=status["daily_pnl"],
            unrealized_pnl=0.0,  # Would calculate from IBKR
            zscore=status["zscore"],
        )


# Import signals at the end
from .signals import SignalGenerator
