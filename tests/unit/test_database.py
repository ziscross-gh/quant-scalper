"""
Unit tests for bot/persistence/database.py - Database operations
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path

from bot.persistence.database import (
    Database, Trade, Signal, Event, TradeStatus, SignalType
)


class TestDatabase:
    """Test Database initialization and basic operations"""

    @pytest.fixture
    def db_path(self, temp_dir):
        """Create temporary database path"""
        return temp_dir / "test_trades.db"

    @pytest.fixture
    def database(self, db_path):
        """Create database instance"""
        db = Database(str(db_path))
        db.init_db()
        yield db
        db.close()

    def test_database_initialization(self, db_path, database):
        """Test that database file is created"""
        assert db_path.exists()

    def test_init_db_creates_tables(self, database):
        """Test that init_db creates all required tables"""
        # Query tables
        tables = database.get_all_tables()

        # Should have trades, signals, and events tables
        assert "trades" in tables
        assert "signals" in tables
        assert "events" in tables

    def test_log_trade(self, database):
        """Test logging a trade"""
        trade_id = database.log_trade(
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.5,
            timestamp=datetime.now(timezone.utc)
        )

        assert trade_id is not None
        assert trade_id > 0

    def test_retrieve_trade(self, database):
        """Test retrieving a logged trade"""
        # Log trade
        timestamp = datetime.now(timezone.utc)
        trade_id = database.log_trade(
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.5,
            timestamp=timestamp
        )

        # Retrieve trade
        trade = database.get_trade(trade_id)

        assert trade is not None
        assert trade.id == trade_id
        assert trade.symbol == "MES"
        assert trade.action == "BUY"
        assert trade.quantity == 1
        assert trade.price == 5000.0
        assert trade.zscore == 2.5

    def test_update_trade_exit(self, database):
        """Test updating trade with exit information"""
        # Log entry trade
        trade_id = database.log_trade(
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.5,
            timestamp=datetime.now(timezone.utc)
        )

        # Update with exit
        exit_time = datetime.now(timezone.utc)
        database.update_trade_exit(
            trade_id=trade_id,
            exit_price=5010.0,
            exit_time=exit_time,
            pnl=50.0,  # (5010 - 5000) * 1 * 5 multiplier
            exit_reason="Z-Score returned to mean"
        )

        # Retrieve updated trade
        trade = database.get_trade(trade_id)

        assert trade.exit_price == 5010.0
        assert trade.pnl == 50.0
        assert trade.exit_reason == "Z-Score returned to mean"
        assert trade.status == TradeStatus.CLOSED

    def test_log_signal(self, database):
        """Test logging a trading signal"""
        signal_id = database.log_signal(
            signal_type="LONG",
            price=5000.0,
            zscore=2.5,
            volume=1000,
            reason="Z-Score >= 2.0",
            timestamp=datetime.now(timezone.utc)
        )

        assert signal_id is not None
        assert signal_id > 0

    def test_retrieve_signal(self, database):
        """Test retrieving a logged signal"""
        timestamp = datetime.now(timezone.utc)
        signal_id = database.log_signal(
            signal_type="SHORT",
            price=5010.0,
            zscore=-2.3,
            volume=1500,
            reason="Z-Score <= -2.0",
            timestamp=timestamp
        )

        signal = database.get_signal(signal_id)

        assert signal is not None
        assert signal.signal_type == "SHORT"
        assert signal.price == 5010.0
        assert signal.zscore == -2.3
        assert signal.volume == 1500

    def test_log_event(self, database):
        """Test logging an event"""
        event_id = database.log_event(
            event_type="CIRCUIT_BREAKER",
            description="Daily loss limit reached",
            severity="CRITICAL",
            timestamp=datetime.now(timezone.utc)
        )

        assert event_id is not None
        assert event_id > 0

    def test_retrieve_event(self, database):
        """Test retrieving a logged event"""
        timestamp = datetime.now(timezone.utc)
        event_id = database.log_event(
            event_type="CONNECTION",
            description="Connected to IBKR Gateway",
            severity="INFO",
            timestamp=timestamp
        )

        event = database.get_event(event_id)

        assert event is not None
        assert event.event_type == "CONNECTION"
        assert event.description == "Connected to IBKR Gateway"
        assert event.severity == "INFO"

    def test_get_all_trades(self, database):
        """Test retrieving all trades"""
        # Log multiple trades
        for i in range(5):
            database.log_trade(
                symbol="MES",
                action="BUY" if i % 2 == 0 else "SELL",
                quantity=1,
                price=5000.0 + i,
                signal_type="LONG" if i % 2 == 0 else "SHORT",
                zscore=2.0 + (i * 0.1),
                timestamp=datetime.now(timezone.utc)
            )

        trades = database.get_all_trades()

        assert len(trades) == 5

    def test_get_trades_by_status(self, database):
        """Test filtering trades by status"""
        # Create some closed and open trades
        trade1 = database.log_trade(
            symbol="MES", action="BUY", quantity=1,
            price=5000.0, signal_type="LONG", zscore=2.0,
            timestamp=datetime.now(timezone.utc)
        )

        trade2 = database.log_trade(
            symbol="MES", action="BUY", quantity=1,
            price=5005.0, signal_type="LONG", zscore=2.1,
            timestamp=datetime.now(timezone.utc)
        )

        # Close first trade
        database.update_trade_exit(
            trade_id=trade1,
            exit_price=5010.0,
            exit_time=datetime.now(timezone.utc),
            pnl=50.0
        )

        # Get open trades
        open_trades = database.get_trades_by_status(TradeStatus.OPEN)
        assert len(open_trades) == 1
        assert open_trades[0].id == trade2

        # Get closed trades
        closed_trades = database.get_trades_by_status(TradeStatus.CLOSED)
        assert len(closed_trades) == 1
        assert closed_trades[0].id == trade1

    def test_get_daily_pnl(self, database):
        """Test calculating daily P&L"""
        today = datetime.now(timezone.utc)

        # Log trades with P&L
        trade1 = database.log_trade(
            symbol="MES", action="BUY", quantity=1,
            price=5000.0, signal_type="LONG", zscore=2.0,
            timestamp=today
        )
        database.update_trade_exit(
            trade_id=trade1,
            exit_price=5010.0,
            exit_time=today,
            pnl=50.0
        )

        trade2 = database.log_trade(
            symbol="MES", action="SELL", quantity=1,
            price=5010.0, signal_type="SHORT", zscore=-2.0,
            timestamp=today
        )
        database.update_trade_exit(
            trade_id=trade2,
            exit_price=5005.0,
            exit_time=today,
            pnl=25.0
        )

        # Calculate daily P&L
        daily_pnl = database.get_daily_pnl(today.date())

        assert daily_pnl == 75.0  # 50 + 25

    def test_get_trade_statistics(self, database):
        """Test getting trade statistics"""
        today = datetime.now(timezone.utc)

        # Log winning and losing trades
        for i in range(3):
            trade_id = database.log_trade(
                symbol="MES", action="BUY", quantity=1,
                price=5000.0, signal_type="LONG", zscore=2.0,
                timestamp=today
            )
            database.update_trade_exit(
                trade_id=trade_id,
                exit_price=5010.0 if i < 2 else 4990.0,  # 2 wins, 1 loss
                exit_time=today,
                pnl=50.0 if i < 2 else -50.0
            )

        stats = database.get_trade_statistics()

        assert stats["total_trades"] == 3
        assert stats["winning_trades"] == 2
        assert stats["losing_trades"] == 1
        assert stats["win_rate"] == pytest.approx(66.67, rel=0.1)
        assert stats["total_pnl"] == 50.0  # 50 + 50 - 50


class TestTradeModel:
    """Test Trade model/dataclass"""

    def test_trade_creation(self):
        """Test creating a Trade object"""
        trade = Trade(
            id=1,
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.5,
            timestamp=datetime.now(timezone.utc),
            status=TradeStatus.OPEN
        )

        assert trade.id == 1
        assert trade.symbol == "MES"
        assert trade.action == "BUY"
        assert trade.status == TradeStatus.OPEN

    def test_trade_to_dict(self):
        """Test converting trade to dictionary"""
        timestamp = datetime.now(timezone.utc)
        trade = Trade(
            id=1,
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.5,
            timestamp=timestamp,
            status=TradeStatus.OPEN
        )

        trade_dict = trade.to_dict()

        assert trade_dict["id"] == 1
        assert trade_dict["symbol"] == "MES"
        assert trade_dict["action"] == "BUY"
        assert "timestamp" in trade_dict


class TestSignalModel:
    """Test Signal model/dataclass"""

    def test_signal_creation(self):
        """Test creating a Signal object"""
        signal = Signal(
            id=1,
            signal_type="LONG",
            price=5000.0,
            zscore=2.5,
            volume=1000,
            reason="Z-Score >= 2.0",
            timestamp=datetime.now(timezone.utc)
        )

        assert signal.id == 1
        assert signal.signal_type == "LONG"
        assert signal.price == 5000.0
        assert signal.zscore == 2.5


class TestEventModel:
    """Test Event model/dataclass"""

    def test_event_creation(self):
        """Test creating an Event object"""
        event = Event(
            id=1,
            event_type="CIRCUIT_BREAKER",
            description="Daily loss limit",
            severity="CRITICAL",
            timestamp=datetime.now(timezone.utc)
        )

        assert event.id == 1
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.severity == "CRITICAL"


class TestDatabaseEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def database(self, temp_dir):
        db = Database(str(temp_dir / "test.db"))
        db.init_db()
        yield db
        db.close()

    def test_get_nonexistent_trade(self, database):
        """Test retrieving a trade that doesn't exist"""
        trade = database.get_trade(99999)

        assert trade is None

    def test_update_nonexistent_trade(self, database):
        """Test updating a trade that doesn't exist"""
        # Should handle gracefully
        database.update_trade_exit(
            trade_id=99999,
            exit_price=5000.0,
            exit_time=datetime.now(timezone.utc),
            pnl=0.0
        )

        # Should not raise error

    def test_negative_pnl(self, database):
        """Test logging trade with negative P&L"""
        trade_id = database.log_trade(
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.0,
            timestamp=datetime.now(timezone.utc)
        )

        database.update_trade_exit(
            trade_id=trade_id,
            exit_price=4990.0,
            exit_time=datetime.now(timezone.utc),
            pnl=-50.0  # Negative
        )

        trade = database.get_trade(trade_id)
        assert trade.pnl == -50.0

    def test_very_large_zscore(self, database):
        """Test handling very large Z-Score values"""
        trade_id = database.log_trade(
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=999.99,  # Very large
            timestamp=datetime.now(timezone.utc)
        )

        trade = database.get_trade(trade_id)
        assert trade.zscore == 999.99

    def test_zero_volume_signal(self, database):
        """Test logging signal with zero volume"""
        signal_id = database.log_signal(
            signal_type="NONE",
            price=5000.0,
            zscore=0.0,
            volume=0,  # Zero volume
            reason="Volume filter",
            timestamp=datetime.now(timezone.utc)
        )

        signal = database.get_signal(signal_id)
        assert signal.volume == 0

    def test_special_characters_in_description(self, database):
        """Test handling special characters in text fields"""
        event_id = database.log_event(
            event_type="ERROR",
            description="Error: Can't connect to 'server' (timeout)",
            severity="ERROR",
            timestamp=datetime.now(timezone.utc)
        )

        event = database.get_event(event_id)
        assert "Can't" in event.description
        assert "'" in event.description

    def test_concurrent_writes(self, database):
        """Test multiple rapid writes"""
        trade_ids = []

        for i in range(100):
            trade_id = database.log_trade(
                symbol="MES",
                action="BUY",
                quantity=1,
                price=5000.0 + i,
                signal_type="LONG",
                zscore=2.0,
                timestamp=datetime.now(timezone.utc)
            )
            trade_ids.append(trade_id)

        # All trades should be logged
        assert len(trade_ids) == 100
        assert len(set(trade_ids)) == 100  # All unique

    def test_database_reopen(self, temp_dir):
        """Test closing and reopening database"""
        db_path = temp_dir / "reopen_test.db"

        # Create and close database
        db1 = Database(str(db_path))
        db1.init_db()
        trade_id = db1.log_trade(
            symbol="MES",
            action="BUY",
            quantity=1,
            price=5000.0,
            signal_type="LONG",
            zscore=2.0,
            timestamp=datetime.now(timezone.utc)
        )
        db1.close()

        # Reopen database
        db2 = Database(str(db_path))
        db2.init_db()

        # Should be able to retrieve trade
        trade = db2.get_trade(trade_id)
        assert trade is not None
        assert trade.id == trade_id

        db2.close()

    def test_empty_daily_pnl(self, database):
        """Test getting daily P&L when no trades"""
        from datetime import date

        pnl = database.get_daily_pnl(date.today())

        # Should be 0 or None
        assert pnl == 0.0 or pnl is None

    def test_statistics_no_trades(self, database):
        """Test statistics when no trades exist"""
        stats = database.get_trade_statistics()

        assert stats["total_trades"] == 0
        assert stats["winning_trades"] == 0
        assert stats["losing_trades"] == 0
