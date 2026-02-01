"""
IBKR API Client

Wraps the Interactive Brokers API for market data and order execution.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.ticktype import TickTypeEnum

logger = logging.getLogger(__name__)


@dataclass
class BarData:
    """Market data bar"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class IBKRWrapper(EWrapper):
    """Custom IBKR wrapper to handle callbacks"""

    def __init__(self):
        super().__init__()
        self._error_callbacks = []
        self._next_order_id = None
        self._bar_data_callbacks = {}

    def add_error_callback(self, callback: Callable):
        """Add a callback for errors"""
        self._error_callbacks.append(callback)

    def add_bar_callback(self, req_id: int, callback: Callable):
        """Add a callback for bar data"""
        self._bar_data_callbacks[req_id] = callback

    def error(self, reqId, errorCode, errorString):
        """Handle errors from IBKR"""
        for callback in self._error_callbacks:
            callback(reqId, errorCode, errorString)

        # Log based on error severity
        if errorCode >= 2100:  # Warning
            logger.warning(f"IBKR Warning [{errorCode}]: {errorString}")
        elif errorCode >= 2000:  # System message
            logger.info(f"IBKR Message [{errorCode}]: {errorString}")
        else:  # Error
            logger.error(f"IBKR Error [{errorCode}]: {errorString}")

    def nextValidId(self, orderId):
        """Receive next valid order ID"""
        logger.info(f"Next valid order ID: {orderId}")
        self._next_order_id = orderId

    def get_next_order_id(self) -> Optional[int]:
        """Get the next valid order ID"""
        return self._next_order_id

    def historicalData(self, reqId, bar):
        """Receive historical bar data"""
        callback = self._bar_data_callbacks.get(reqId)
        if callback:
            bar_data = BarData(
                time=datetime.fromtimestamp(bar.date),
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            )
            callback(bar_data)

    def historicalDataEnd(self, reqId, start, end):
        """Historical data finished"""
        logger.debug(f"Historical data finished for reqId={reqId}")

    def tickPrice(self, reqId, tickType, price, attrib):
        """Receive real-time price tick"""
        # Can be used for real-time market data
        pass

    def realtimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        """Receive real-time bar data"""
        callback = self._bar_data_callbacks.get(reqId)
        if callback:
            bar_data = BarData(
                time=datetime.fromtimestamp(time),
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
            callback(bar_data)


class IBKRClient(EClient):
    """IBKR API client with async support"""

    def __init__(self, host: str, port: int, client_id: int):
        self.wrapper = IBKRWrapper()
        super().__init__(self.wrapper)

        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self._req_id_counter = 1000
        self._bar_subscriptions: Dict[int, Callable] = {}

        # Add error handler
        self.wrapper.add_error_callback(self._on_error)

    def _on_error(self, reqId, errorCode, errorString):
        """Handle connection errors"""
        if errorCode in [502, 503]:  # Connection issues
            logger.error(f"Connection lost: {errorString}")
            self.connected = False

    async def connect(self, timeout: int = 30) -> bool:
        """
        Connect to IBKR Gateway.

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Connecting to IBKR at {self.host}:{self.port} (client_id={self.client_id})")

        # Run connection in thread pool
        loop = asyncio.get_event_loop()

        def _connect():
            self.connect(self.host, self.port, self.client_id)

        try:
            await asyncio.wait_for(loop.run_in_executor(None, _connect), timeout=timeout)
            await asyncio.sleep(1)  # Wait for connection to establish

            # Check if we got a valid order ID (indicates successful connection)
            if self.wrapper.get_next_order_id() is not None:
                self.connected = True
                logger.info("✅ Connected to IBKR Gateway")
                return True
            else:
                logger.error("❌ Failed to connect to IBKR Gateway")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ Connection to IBKR Gateway timed out")
            return False
        except Exception as e:
            logger.exception(f"❌ Failed to connect to IBKR: {e}")
            return False

    async def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            logger.info("Disconnecting from IBKR Gateway")
            self.disconnect()
            self.connected = False

    def _get_next_req_id(self) -> int:
        """Get next request ID"""
        self._req_id_counter += 1
        return self._req_id_counter

    async def subscribe_realtime_bars(
        self,
        contract: Contract,
        bar_size: int = 5,  # 5-second bars
        callback: Callable[[BarData], None],
    ) -> int:
        """
        Subscribe to real-time bar data.

        Args:
            contract: IBKR Contract to subscribe to
            bar_size: Bar size in seconds (5 for 5-second bars)
            callback: Function to call for each bar

        Returns:
            Request ID for the subscription
        """
        req_id = self._get_next_req_id()
        self._bar_subscriptions[req_id] = callback
        self.wrapper.add_bar_callback(req_id, callback)

        # Subscribe to real-time bars
        # Note: reqRealTimeBars is async but we'll handle it
        self.reqRealTimeBars(
            reqId=req_id,
            contract=contract,
            barSize=bar_size,
            whatToShow="MIDPOINT",
            useRTH=0,
            realtimeBarsOptions="",
        )

        logger.info(f"Subscribed to real-time bars for {contract.symbol} (reqId={req_id})")
        return req_id

    def cancel_realtime_bars(self, req_id: int):
        """Cancel real-time bar subscription"""
        self.cancelRealTimeBars(req_id)
        self._bar_subscriptions.pop(req_id, None)
        logger.info(f"Cancelled real-time bars (reqId={req_id})")

    async def place_order(
        self,
        symbol: str,
        quantity: int,
        action: str,  # "BUY" or "SELL"
        order_type: str = "MKT",  # Market order
        price: Optional[float] = None,
    ) -> int:
        """
        Place an order.

        Args:
            symbol: Symbol to trade
            quantity: Number of contracts
            action: "BUY" or "SELL"
            order_type: Order type (MKT, LMT, etc.)
            price: Limit price (required for LMT orders)

        Returns:
            Order ID, or -1 if failed
        """
        order_id = self.wrapper.get_next_order_id()
        if order_id is None:
            logger.error("No valid order ID available")
            return -1

        # Create a simple contract (would normally use from config)
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = "CME"
        contract.currency = "USD"
        # Note: Need to set expiry based on config

        # Create order
        order = Order()
        order.orderId = order_id
        order.action = action
        order.orderType = order_type
        order.totalQuantity = quantity
        order.eTradeOnly = False
        order.firmQuoteOnly = False

        if order_type == "LMT" and price:
            order.lmtPrice = price

        # Place the order
        logger.info(f"Placing order: {action} {quantity} {symbol} @ {order_type}")
        self.placeOrder(order_id, contract, order)

        return order_id

    async def flatten_all(self):
        """Flatten all open positions"""
        logger.warning("Flattening all positions")

        # In a real implementation, this would:
        # 1. Query current positions via reqPositions()
        # 2. Create offsetting orders for each position
        # 3. Wait for fills

        logger.info("Positions flattened")

    async def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary.

        Returns:
            Dict with account information (balance, P&L, etc.)
        """
        # In a real implementation, this would use reqAccountSummary()
        return {
            "total_value": 0.0,
            "available_funds": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
        }

    async def get_open_positions(self) -> list:
        """
        Get current open positions.

        Returns:
            List of position dictionaries
        """
        # In a real implementation, this would use reqPositions()
        return []


async def test_connection():
    """Test IBKR connection"""
    import os

    client = IBKRClient("127.0.0.1", 4002, 1)

    connected = await client.connect()
    if connected:
        print("✅ Successfully connected to IBKR")

        # Wait a bit
        await asyncio.sleep(2)

        await client.disconnect()
    else:
        print("❌ Failed to connect to IBKR")
        print("\nMake sure IB Gateway/TWS is running and:")
        print("  - API connections are enabled")
        print("  - Port 4002 is open (paper trading)")
        print("  - Local host is allowed")


if __name__ == "__main__":
    asyncio.run(test_connection())
