"""
Main Entry Point

Starts the trading bot with IBKR connection, signal generation, and Telegram alerts.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from .config import Config
from .core.engine import TradingEngine
from .alerts.telegram import TelegramAlertManager
from .ibkr.client import IBKRClient
from .persistence.database import TradeDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
        self.alerts = None
        self.engine = None
        self.ibkr_client = None
        self.database = None

        self._shutdown_event = asyncio.Event()
        self._running = False

    async def initialize(self):
        """Initialize bot components"""
        logger.info("=" * 60)
        logger.info("🤖 Quant Scalping Bot Starting")
        logger.info("=" * 60)

        # Load configuration
        logger.info(f"Loading configuration from {self.config_path}")
        self.config = Config.load(self.config_path)

        # Validate configuration
        errors = self.config.validate()
        if errors:
            logger.error("Configuration errors found:")
            for error in errors:
                logger.error(f"  ❌ {error}")
            raise ValueError("Invalid configuration")

        # Initialize database
        logger.info("Initializing database...")
        self.database = TradeDatabase(self.config.database.url)
        self.database.connect()

        # Initialize alerts
        logger.info("Initializing Telegram alerts...")
        self.alerts = TelegramAlertManager(self.config.telegram)
        await self.alerts.start()

        # Initialize trading engine
        logger.info("Initializing trading engine...")
        self.engine = TradingEngine(self.config, self.alerts)

        # Initialize IBKR client
        logger.info("Initializing IBKR client...")
        self.ibkr_client = IBKRClient(
            host=self.config.ibkr.host,
            port=self.config.ibkr.port,
            client_id=self.config.ibkr.client_id,
        )

        # Connect IBKR client to engine
        self.engine.set_ibkr_client(self.ibkr_client)

        logger.info("✅ Initialization complete")

    async def connect(self):
        """Connect to IBKR"""
        logger.info("Connecting to IBKR Gateway...")

        max_attempts = self.config.ibkr.max_reconnect_attempts
        for attempt in range(1, max_attempts + 1):
            connected = await self.ibkr_client.connect()

            if connected:
                await self.alerts.send_connected()
                return True

            logger.warning(f"Connection attempt {attempt}/{max_attempts} failed")
            if attempt < max_attempts:
                await asyncio.sleep(self.config.ibkr.reconnect_delay)

        await self.alerts.send_error("Failed to connect to IBKR after max attempts")
        return False

    async def run(self):
        """Main trading loop"""
        logger.info("Starting main trading loop...")

        await self.engine.start()
        self._running = True

        try:
            while not self._shutdown_event.is_set():
                # In a real implementation, this would:
                # 1. Subscribe to real-time bars
                # 2. Process each bar through the engine
                # 3. Execute orders based on signals
                # 4. Check risk limits
                # 5. Send periodic status updates

                # For now, simulate with a heartbeat
                await asyncio.sleep(5)

                # Check risk limits
                await self.engine.check_risk_limits()

                # Send daily summary at midnight (simplified)
                if datetime.utcnow().hour == 0 and datetime.utcnow().minute == 0:
                    await self._send_daily_summary()

        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.exception("Fatal error in main loop")
            await self.alerts.send_error(f"Fatal error: {str(e)}")
            raise

    async def _send_daily_summary(self):
        """Send daily trading summary"""
        stats = self.engine.state.daily_stats

        # Calculate win rate and profit factor
        total_trades = stats.winning_trades + stats.losing_trades
        win_rate = (stats.winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        profit_factor = None  # Would calculate from database

        await self.alerts.send_daily_summary(
            net_pnl=stats.realized_pnl,
            trades_count=stats.trades_count,
            win_rate=win_rate,
            winning=stats.winning_trades,
            losing=stats.losing_trades,
            profit_factor=profit_factor,
        )

    async def shutdown(self, reason: str = "Shutdown signal received"):
        """Graceful shutdown"""
        if not self._running:
            return

        logger.info(f"Shutting down: {reason}")
        self._running = False
        self._shutdown_event.set()

        # Stop engine
        await self.engine.stop(reason)

        # Disconnect IBKR
        if self.ibkr_client:
            await self.ibkr_client.disconnect_async()

        # Stop alerts
        if self.alerts:
            await self.alerts.stop()

        # Close database
        if self.database:
            self.database.disconnect()

        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m bot.main <config_path>")
        print("Example: python -m bot.main config/config.yaml")
        sys.exit(1)

    config_path = sys.argv[1]

    # Create bot
    bot = TradingBot(config_path)

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(bot.shutdown("Signal received"))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize
        await bot.initialize()

        # Connect to IBKR
        if not await bot.connect():
            logger.error("Failed to connect to IBKR")
            sys.exit(1)

        # Run main loop
        await bot.run()

    except Exception as e:
        logger.exception("Fatal error")
        sys.exit(1)
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
