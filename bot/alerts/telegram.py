"""
Telegram Alert Integration

Sends notifications for:
- Trade entries/exits
- Daily summaries
- Circuit breaker triggers
- Errors and warnings
"""
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class TelegramAlertManager:
    """Manages Telegram notifications"""
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.base_url = self.BASE_URL.format(token=config.bot_token)
        self.session: Optional[aiohttp.ClientSession] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the alert manager"""
        if not self.config.enabled:
            logger.info("Telegram alerts disabled")
            return
        
        self.session = aiohttp.ClientSession()
        self._worker_task = asyncio.create_task(self._message_worker())
        logger.info("Telegram alert manager started")
    
    async def stop(self):
        """Stop the alert manager"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
    
    async def _message_worker(self):
        """Background worker to send queued messages"""
        while True:
            try:
                text, parse_mode = await self._queue.get()
                await self._send_message_impl(text, parse_mode)
                self._queue.task_done()
                # Rate limit: max 30 messages per second
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in message worker: {e}")
    
    async def _send_message_impl(self, text: str, parse_mode: str = "HTML"):
        """Actually send the message"""
        if not self.config.enabled or not self.session:
            return
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.config.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Telegram API error: {error_text}")
        except Exception as e:
            logger.exception(f"Failed to send Telegram message: {e}")
    
    def send(self, text: str, parse_mode: str = "HTML"):
        """Queue a message for sending (non-blocking)"""
        if self.config.enabled:
            self._queue.put_nowait((text, parse_mode))
    
    async def send_async(self, text: str, parse_mode: str = "HTML"):
        """Send a message and wait for it to be queued"""
        if self.config.enabled:
            await self._queue.put((text, parse_mode))
    
    # ==================== Message Templates ====================
    
    async def send_startup(self, mode: str, instrument: str, max_loss: float):
        """Send startup notification"""
        mode_emoji = "🟢 PAPER" if mode == "paper" else "🔴 LIVE"
        message = f"""
<b>🤖 Bot Started</b>

Mode: {mode_emoji}
Instrument: <code>{instrument}</code>
Max Daily Loss: <code>${max_loss:.0f}</code>

<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
"""
        await self.send_async(message)
    
    async def send_connected(self):
        """Send IBKR connection notification"""
        self.send("✅ Connected to IBKR Gateway")
    
    async def send_disconnected(self):
        """Send disconnection notification"""
        self.send("⚠️ Disconnected from IBKR Gateway - attempting reconnect...")
    
    async def send_trade_entry(
        self,
        direction: str,
        symbol: str,
        quantity: int,
        price: float,
        zscore: float,
        reason: str,
    ):
        """Send trade entry notification"""
        emoji = "📈" if direction == "LONG" else "📉"
        message = f"""
<b>{emoji} Trade Entry</b>

Direction: <code>{direction}</code>
Symbol: <code>{symbol}</code>
Quantity: <code>{quantity}</code>
Price: <code>{price:.2f}</code>
Z-Score: <code>{zscore:.2f}</code>

Reason: {reason}

<i>{datetime.utcnow().strftime('%H:%M:%S')} UTC</i>
"""
        await self.send_async(message)
    
    async def send_trade_exit(
        self,
        symbol: str,
        exit_price: float,
        pnl: float,
        zscore: float,
    ):
        """Send trade exit notification"""
        emoji = "💰" if pnl >= 0 else "💸"
        pnl_sign = "+" if pnl >= 0 else ""
        message = f"""
<b>{emoji} Trade Exit</b>

Symbol: <code>{symbol}</code>
Exit Price: <code>{exit_price:.2f}</code>
P&L: <code>{pnl_sign}${pnl:.2f}</code>
Z-Score: <code>{zscore:.2f}</code>

<i>{datetime.utcnow().strftime('%H:%M:%S')} UTC</i>
"""
        await self.send_async(message)
    
    async def send_circuit_breaker(self, reason: str):
        """Send circuit breaker notification"""
        reasons = {
            "daily_loss_limit": "📛 Daily loss limit reached",
            "consecutive_losses": "📛 Too many consecutive losses",
            "position_timeout": "⏰ Position held too long",
            "connection_lost": "🔌 Connection lost",
        }
        reason_text = reasons.get(reason, reason)
        
        message = f"""
<b>⚠️ CIRCUIT BREAKER TRIGGERED</b>

Reason: {reason_text}
Action: All positions flattened, trading halted

<i>{datetime.utcnow().strftime('%H:%M:%S')} UTC</i>
"""
        await self.send_async(message)
    
    async def send_daily_summary(
        self,
        net_pnl: float,
        trades_count: int,
        win_rate: float,
        winning: int,
        losing: int,
        profit_factor: Optional[float],
    ):
        """Send daily summary"""
        emoji = "🟢" if net_pnl >= 0 else "🔴"
        pnl_sign = "+" if net_pnl >= 0 else ""
        pf_text = f"{profit_factor:.2f}" if profit_factor else "N/A"
        
        message = f"""
<b>📊 Daily Summary</b>

{emoji} Net P&L: <code>{pnl_sign}${net_pnl:.2f}</code>
Trades: <code>{trades_count}</code>
Win Rate: <code>{win_rate:.1f}%</code>
Winners: <code>{winning}</code>
Losers: <code>{losing}</code>
Profit Factor: <code>{pf_text}</code>

<i>{datetime.utcnow().strftime('%Y-%m-%d')}</i>
"""
        await self.send_async(message)
    
    async def send_error(self, error: str):
        """Send error notification"""
        # Truncate long error messages
        if len(error) > 500:
            error = error[:500] + "..."
        
        message = f"""
<b>🚨 ERROR</b>

<code>{error}</code>

<i>{datetime.utcnow().strftime('%H:%M:%S')} UTC</i>
"""
        await self.send_async(message)
    
    async def send_shutdown(self, reason: str = "Manual"):
        """Send shutdown notification"""
        message = f"""
<b>🛑 Bot Shutting Down</b>

Reason: {reason}

<i>{datetime.utcnow().strftime('%H:%M:%S')} UTC</i>
"""
        await self.send_async(message)
    
    async def send_status(
        self,
        state: str,
        position: int,
        daily_pnl: float,
        unrealized_pnl: float,
        zscore: Optional[float],
    ):
        """Send current status (for /status command)"""
        state_emoji = {
            "running": "🟢",
            "paused": "⏸️",
            "stopped": "🔴",
            "error": "🚨",
        }.get(state, "❓")
        
        pos_text = "None" if position == 0 else f"{'LONG' if position > 0 else 'SHORT'} x{abs(position)}"
        z_text = f"{zscore:.2f}" if zscore is not None else "Warming up..."
        
        message = f"""
<b>🤖 Bot Status</b>

State: {state_emoji} {state.upper()}
Position: <code>{pos_text}</code>
Daily P&L: <code>${daily_pnl:+.2f}</code>
Unrealized: <code>${unrealized_pnl:+.2f}</code>
Z-Score: <code>{z_text}</code>

<i>{datetime.utcnow().strftime('%H:%M:%S')} UTC</i>
"""
        await self.send_async(message)


# Standalone test
if __name__ == "__main__":
    import os
    
    async def test():
        config = TelegramConfig(
            enabled=True,
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )
        
        if not config.bot_token or not config.chat_id:
            print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
            return
        
        alerts = TelegramAlertManager(config)
        await alerts.start()
        
        await alerts.send_startup("paper", "MES", 500.0)
        await asyncio.sleep(1)
        
        await alerts.stop()
        print("Test complete!")
    
    asyncio.run(test())
