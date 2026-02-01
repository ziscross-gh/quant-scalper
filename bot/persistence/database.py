"""
Database Persistence

Logs trades and state to SQLite database for analysis and recovery.
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """A trade record"""
    id: int
    timestamp: datetime
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: int
    price: float
    order_id: int
    pnl: Optional[float] = None
    zscore: Optional[float] = None


class TradeDatabase:
    """SQLite database for trade logging"""

    def __init__(self, db_path: str = "data/trades.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None

    def connect(self):
        """Connect to database and create tables"""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        # Create tables
        self._create_tables()

    def _create_tables(self):
        """Create database tables"""
        cursor = self._conn.cursor()

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                order_id INTEGER NOT NULL,
                exit_price REAL,
                pnl REAL,
                zscore REAL,
                exit_reason TEXT
            )
        """)

        # Daily summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                trades_count INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                realized_pnl REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0
            )
        """)

        # Bot state table (for recovery)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        self._conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def disconnect(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def log_trade(self, trade: Dict[str, Any]) -> int:
        """
        Log a trade to the database.

        Args:
            trade: Trade dict with keys: symbol, action, quantity, price, order_id, etc.

        Returns:
            Trade ID
        """
        cursor = self._conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                timestamp, symbol, action, quantity, price,
                order_id, pnl, zscore, exit_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            trade.get("symbol", ""),
            trade.get("action", ""),
            trade.get("quantity", 0),
            trade.get("price", 0.0),
            trade.get("order_id", 0),
            trade.get("pnl"),
            trade.get("zscore"),
            trade.get("exit_reason"),
        ))

        self._conn.commit()
        trade_id = cursor.lastrowid
        logger.debug(f"Logged trade #{trade_id}: {trade.get('action')} {trade.get('quantity')} {trade.get('symbol')}")

        return trade_id

    def update_trade_exit(self, trade_id: int, exit_price: float, pnl: float, reason: str = ""):
        """
        Update trade with exit information.

        Args:
            trade_id: Trade ID to update
            exit_price: Exit price
            pnl: Profit/loss
            reason: Exit reason
        """
        cursor = self._conn.cursor()

        cursor.execute("""
            UPDATE trades
            SET exit_price = ?, pnl = ?, exit_reason = ?
            WHERE id = ?
        """, (exit_price, pnl, reason, trade_id))

        self._conn.commit()
        logger.debug(f"Updated trade #{trade_id} with exit: ${pnl:+.2f}")

    def get_trades(
        self,
        limit: Optional[int] = None,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Trade]:
        """
        Get trades from database.

        Args:
            limit: Maximum number of trades to return
            symbol: Filter by symbol
            start_date: Filter trades after this date
            end_date: Filter trades before this date

        Returns:
            List of Trade objects
        """
        cursor = self._conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY timestamp DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)

        trades = []
        for row in cursor.fetchall():
            trades.append(Trade(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                symbol=row["symbol"],
                action=row["action"],
                quantity=row["quantity"],
                price=row["price"],
                order_id=row["order_id"],
                pnl=row["pnl"],
                zscore=row["zscore"],
            ))

        return trades

    def get_daily_stats(self, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Get daily statistics for a date.

        Args:
            date: Date to get stats for (default: today)

        Returns:
            Dict with daily stats or None if not found
        """
        if date is None:
            date = datetime.utcnow().date()

        cursor = self._conn.cursor()

        cursor.execute("""
            SELECT * FROM daily_summary WHERE date = ?
        """, (date.isoformat(),))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def update_daily_summary(self, date: Optional[datetime] = None, **updates):
        """
        Update daily summary.

        Args:
            date: Date to update (default: today)
            **updates: Fields to update (trades_count, winning_trades, etc.)
        """
        if date is None:
            date = datetime.utcnow().date()

        cursor = self._conn.cursor()

        # Check if exists
        cursor.execute("""
            SELECT date FROM daily_summary WHERE date = ?
        """, (date.isoformat(),))

        if cursor.fetchone():
            # Update existing
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [date.isoformat()]
            cursor.execute(f"""
                UPDATE daily_summary
                SET {set_clause}
                WHERE date = ?
            """, values)
        else:
            # Insert new
            columns = ["date"] + list(updates.keys())
            placeholders = ", ".join(["?"] * len(columns))
            values = [date.isoformat()] + list(updates.values())
            cursor.execute(f"""
                INSERT INTO daily_summary ({", ".join(columns)})
                VALUES ({placeholders})
            """, values)

        self._conn.commit()

    def save_state(self, key: str, value: str):
        """
        Save bot state to database.

        Args:
            key: State key
            value: State value (JSON string recommended)
        """
        cursor = self._conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO bot_state (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.utcnow().isoformat()))

        self._conn.commit()

    def load_state(self, key: str) -> Optional[str]:
        """
        Load bot state from database.

        Args:
            key: State key

        Returns:
            State value or None if not found
        """
        cursor = self._conn.cursor()

        cursor.execute("""
            SELECT value FROM bot_state WHERE key = ?
        """, (key,))

        row = cursor.fetchone()
        return row["value"] if row else None

    def cleanup_old_data(self, days: int = 30):
        """
        Delete old trades and state data.

        Args:
            days: Keep data newer than this many days
        """
        cursor = self._conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        cursor.execute("""
            DELETE FROM trades WHERE timestamp < ?
        """, (cutoff,))

        cursor.execute("""
            DELETE FROM bot_state WHERE updated_at < ?
        """, (cutoff,))

        self._conn.commit()
        logger.info(f"Cleaned up data older than {days} days")


def test_database():
    """Test database functionality"""
    from datetime import timedelta

    # Create test database
    db = TradeDatabase("data/test_trades.db")
    db.connect()

    # Log some trades
    trade_id = db.log_trade({
        "symbol": "MES",
        "action": "BUY",
        "quantity": 1,
        "price": 5000.0,
        "order_id": 1001,
        "zscore": -2.5,
    })
    print(f"✅ Logged trade #{trade_id}")

    # Update with exit
    db.update_trade_exit(trade_id, exit_price=5025.0, pnl=125.0, reason="Take profit")
    print("✅ Updated trade exit")

    # Get trades
    trades = db.get_trades(limit=5)
    print(f"✅ Retrieved {len(trades)} trades")
    for trade in trades:
        print(f"   {trade.action} {trade.quantity} {trade.symbol} @ ${trade.price:.2f} | P&L: ${trade.pnl or 0:+.2f}")

    # Update daily summary
    db.update_daily_summary(
        trades_count=5,
        winning_trades=3,
        losing_trades=2,
        realized_pnl=250.0,
    )
    print("✅ Updated daily summary")

    # Save/load state
    db.save_state("position", '{"quantity": 1, "entry_price": 5000.0}')
    state = db.load_state("position")
    print(f"✅ Saved/loaded state: {state}")

    db.disconnect()
    print("\n✅ Database test complete!")


if __name__ == "__main__":
    from datetime import timedelta
    test_database()
