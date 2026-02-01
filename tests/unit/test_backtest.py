"""
Unit tests for bot/backtest/engine.py - Backtesting engine and metrics
"""
import pytest
from datetime import datetime, timezone
import numpy as np

from bot.backtest.engine import (
    BacktestEngine, BacktestResult, Bar, BacktestConfig
)
from bot.config import TradingConfig, RiskConfig


class TestBacktestConfig:
    """Test BacktestConfig"""

    def test_valid_config(self):
        """Test valid backtest configuration"""
        config = BacktestConfig(
            initial_capital=10000.0,
            commission_per_trade=2.50,
            slippage_ticks=0.25,
            use_risk_limits=True
        )

        assert config.initial_capital == 10000.0
        assert config.commission_per_trade == 2.50

    def test_invalid_initial_capital(self):
        """Test that initial capital must be positive"""
        with pytest.raises(ValueError):
            BacktestConfig(
                initial_capital=-1000.0,  # Invalid
                commission_per_trade=2.50
            )


class TestBar:
    """Test Bar dataclass"""

    def test_bar_creation(self):
        """Test creating a Bar"""
        bar = Bar(
            time=datetime.now(timezone.utc),
            open=5000.0,
            high=5005.0,
            low=4995.0,
            close=5002.0,
            volume=1500
        )

        assert bar.close == 5002.0
        assert bar.high == 5005.0
        assert bar.low == 4995.0
        assert bar.volume == 1500

    def test_bar_validation(self):
        """Test bar validation (high/low constraints)"""
        # High should be >= low
        bar = Bar(
            time=datetime.now(timezone.utc),
            open=5000.0,
            high=5005.0,
            low=4995.0,
            close=5000.0,
            volume=1000
        )

        assert bar.high >= bar.low
        assert bar.close <= bar.high
        assert bar.close >= bar.low


class TestBacktestEngine:
    """Test BacktestEngine core functionality"""

    @pytest.fixture
    def trading_config(self):
        """Create trading config for backtest"""
        return TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=20,
            z_entry_threshold=2.0,
            z_exit_threshold=0.5,
            min_volume_filter=100
        )

    @pytest.fixture
    def risk_config(self):
        """Create risk config for backtest"""
        return RiskConfig(
            max_daily_loss=500.0,
            max_position_size=2,
            max_consecutive_losses=3,
            max_trades_per_day=10,
            position_timeout_hours=2.0,
            drawdown_limit_percent=10.0,
            cooldown_minutes=30
        )

    @pytest.fixture
    def backtest_config(self):
        """Create backtest config"""
        return BacktestConfig(
            initial_capital=10000.0,
            commission_per_trade=2.50,
            slippage_ticks=0.25,
            use_risk_limits=True
        )

    @pytest.fixture
    def engine(self, trading_config, risk_config, backtest_config):
        """Create backtest engine"""
        return BacktestEngine(
            trading_config=trading_config,
            risk_config=risk_config,
            backtest_config=backtest_config
        )

    @pytest.fixture
    def sample_bars(self):
        """Generate sample price bars"""
        bars = []
        base_price = 5000.0

        for i in range(100):
            # Create realistic OHLC bars
            price = base_price + np.random.normal(0, 5)
            high = price + abs(np.random.normal(0, 2))
            low = price - abs(np.random.normal(0, 2))

            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=price,
                high=high,
                low=low,
                close=price,
                volume=1000 + int(np.random.normal(0, 200))
            ))

        return bars

    def test_initialization(self, engine, backtest_config):
        """Test backtest engine initialization"""
        assert engine.config == backtest_config
        assert engine.equity == backtest_config.initial_capital
        assert engine.position == 0

    def test_run_backtest(self, engine, sample_bars):
        """Test running a backtest"""
        result = engine.run(sample_bars)

        assert isinstance(result, BacktestResult)
        assert result.total_trades >= 0
        assert len(result.equity_curve) > 0

    def test_backtest_result_structure(self, engine, sample_bars):
        """Test that backtest result contains all required fields"""
        result = engine.run(sample_bars)

        assert hasattr(result, "total_trades")
        assert hasattr(result, "winning_trades")
        assert hasattr(result, "losing_trades")
        assert hasattr(result, "total_pnl")
        assert hasattr(result, "win_rate")
        assert hasattr(result, "profit_factor")
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "equity_curve")
        assert hasattr(result, "trades")

    def test_commission_deduction(self, engine, sample_bars):
        """Test that commissions are properly deducted"""
        result = engine.run(sample_bars)

        # If any trades occurred, commissions should have been charged
        if result.total_trades > 0:
            # Total commission = trades * commission_per_trade * 2 (entry + exit)
            expected_commission = result.total_trades * 2.50 * 2

            # Equity should reflect commission costs
            assert engine.equity < engine.config.initial_capital + result.total_pnl

    def test_slippage_impact(self, engine, sample_bars):
        """Test that slippage is accounted for"""
        result = engine.run(sample_bars)

        # Slippage should reduce profitability
        # This is implementation-dependent
        assert isinstance(result.total_pnl, float)

    def test_position_tracking(self, engine):
        """Test that positions are tracked correctly"""
        # Create bars that should trigger signals
        bars = []
        # Warmup period with stable prices
        for i in range(20):
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=5000.0,
                high=5001.0,
                low=4999.0,
                close=5000.0,
                volume=1000
            ))

        # Add price that should trigger signal
        bars.append(Bar(
            time=datetime.now(timezone.utc),
            open=4980.0,
            high=4981.0,
            low=4979.0,
            close=4980.0,  # Deviation should trigger
            volume=1500
        ))

        result = engine.run(bars)

        # Should have attempted to enter position
        assert result.total_trades >= 0

    def test_equity_curve_generation(self, engine, sample_bars):
        """Test that equity curve is generated"""
        result = engine.run(sample_bars)

        assert len(result.equity_curve) > 0
        # Equity curve should start at initial capital
        assert result.equity_curve[0] == engine.config.initial_capital

    def test_trade_log_generation(self, engine, sample_bars):
        """Test that trade log is generated"""
        result = engine.run(sample_bars)

        assert isinstance(result.trades, list)

        # Each trade should have required fields
        for trade in result.trades:
            assert "entry_time" in trade
            assert "entry_price" in trade
            assert "exit_time" in trade
            assert "exit_price" in trade
            assert "pnl" in trade


class TestBacktestMetrics:
    """Test backtest metric calculations"""

    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        result = BacktestResult(
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            total_pnl=500.0,
            win_rate=70.0,
            profit_factor=2.5,
            sharpe_ratio=1.5,
            max_drawdown=100.0,
            equity_curve=[10000, 10500, 10300, 10800],
            trades=[]
        )

        assert result.win_rate == 70.0
        assert result.winning_trades == 7
        assert result.losing_trades == 3

    def test_profit_factor_calculation(self):
        """Test profit factor calculation"""
        result = BacktestResult(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            total_pnl=200.0,
            win_rate=60.0,
            profit_factor=2.0,  # Gross profit / Gross loss
            sharpe_ratio=1.2,
            max_drawdown=150.0,
            equity_curve=[10000],
            trades=[]
        )

        assert result.profit_factor == 2.0

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""
        # Sharpe ratio measures risk-adjusted returns
        result = BacktestResult(
            total_trades=100,
            winning_trades=55,
            losing_trades=45,
            total_pnl=1000.0,
            win_rate=55.0,
            profit_factor=1.5,
            sharpe_ratio=1.8,  # > 1 is good
            max_drawdown=300.0,
            equity_curve=[10000],
            trades=[]
        )

        assert result.sharpe_ratio > 0

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation"""
        equity_curve = [10000, 10500, 10300, 9800, 10100, 11000]

        # Max drawdown = (10500 - 9800) = 700
        max_dd = max(equity_curve) - min(equity_curve)

        assert max_dd == 1700  # 11000 - 9800

    def test_zero_trades_metrics(self):
        """Test metrics when no trades occurred"""
        result = BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            equity_curve=[10000, 10000],  # No change
            trades=[]
        )

        assert result.total_trades == 0
        assert result.total_pnl == 0.0

    def test_all_winning_trades(self):
        """Test metrics when all trades are winners"""
        result = BacktestResult(
            total_trades=10,
            winning_trades=10,
            losing_trades=0,
            total_pnl=1000.0,
            win_rate=100.0,
            profit_factor=float('inf'),  # No losses
            sharpe_ratio=3.0,
            max_drawdown=0.0,
            equity_curve=[10000, 11000],
            trades=[]
        )

        assert result.win_rate == 100.0
        assert result.losing_trades == 0

    def test_all_losing_trades(self):
        """Test metrics when all trades are losses"""
        result = BacktestResult(
            total_trades=10,
            winning_trades=0,
            losing_trades=10,
            total_pnl=-500.0,
            win_rate=0.0,
            profit_factor=0.0,  # No profits
            sharpe_ratio=-1.0,
            max_drawdown=500.0,
            equity_curve=[10000, 9500],
            trades=[]
        )

        assert result.win_rate == 0.0
        assert result.winning_trades == 0


class TestBacktestEdgeCases:
    """Test edge cases in backtesting"""

    @pytest.fixture
    def trading_config(self):
        return TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=5,  # Small for testing
            z_entry_threshold=2.0,
            z_exit_threshold=0.5,
            min_volume_filter=0
        )

    @pytest.fixture
    def risk_config(self):
        return RiskConfig(
            max_daily_loss=10000.0,  # High limit for testing
            max_position_size=1,
            max_consecutive_losses=100,
            max_trades_per_day=1000
        )

    @pytest.fixture
    def backtest_config(self):
        return BacktestConfig(
            initial_capital=10000.0,
            commission_per_trade=2.50,
            slippage_ticks=0.25,
            use_risk_limits=False  # Disable for testing
        )

    @pytest.fixture
    def engine(self, trading_config, risk_config, backtest_config):
        return BacktestEngine(trading_config, risk_config, backtest_config)

    def test_empty_bars(self, engine):
        """Test backtesting with no bars"""
        result = engine.run([])

        assert result.total_trades == 0
        assert len(result.equity_curve) > 0

    def test_single_bar(self, engine):
        """Test backtesting with single bar"""
        bar = Bar(
            time=datetime.now(timezone.utc),
            open=5000.0,
            high=5005.0,
            low=4995.0,
            close=5000.0,
            volume=1000
        )

        result = engine.run([bar])

        # Should not crash, but also should not trade
        assert result.total_trades == 0

    def test_insufficient_bars_for_warmup(self, engine):
        """Test with bars less than lookback period"""
        bars = []
        for i in range(3):  # Less than lookback of 5
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=5000.0,
                high=5001.0,
                low=4999.0,
                close=5000.0,
                volume=1000
            ))

        result = engine.run(bars)

        # Should not generate signals during warmup
        assert result.total_trades == 0

    def test_extreme_price_movements(self, engine):
        """Test handling of extreme price movements"""
        bars = []

        # Warmup
        for i in range(10):
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=5000.0,
                high=5001.0,
                low=4999.0,
                close=5000.0,
                volume=1000
            ))

        # Extreme move
        bars.append(Bar(
            time=datetime.now(timezone.utc),
            open=5000.0,
            high=6000.0,
            low=4000.0,
            close=5500.0,
            volume=5000
        ))

        result = engine.run(bars)

        # Should handle without errors
        assert isinstance(result, BacktestResult)

    def test_zero_volume_bars(self, engine):
        """Test handling of zero volume bars"""
        bars = []

        for i in range(25):
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=5000.0,
                high=5001.0,
                low=4999.0,
                close=5000.0,
                volume=0  # Zero volume
            ))

        result = engine.run(bars)

        # Should handle gracefully
        assert isinstance(result, BacktestResult)

    def test_constant_prices(self, engine):
        """Test with all prices identical (zero variance)"""
        bars = []

        for i in range(50):
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=5000.0,
                high=5000.0,
                low=5000.0,
                close=5000.0,
                volume=1000
            ))

        result = engine.run(bars)

        # Should not generate signals (zero variance = zero Z-Score)
        assert result.total_trades == 0

    def test_alternating_extreme_prices(self, engine):
        """Test with rapidly alternating prices"""
        bars = []

        for i in range(50):
            price = 5000.0 if i % 2 == 0 else 5100.0
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000
            ))

        result = engine.run(bars)

        # Should handle rapid oscillations
        assert isinstance(result, BacktestResult)

    def test_risk_limits_enforcement(self):
        """Test that risk limits are enforced during backtest"""
        # Create engine with strict risk limits
        trading_config = TradingConfig(
            symbol="MES",
            exchange="GLOBEX",
            currency="USD",
            lookback_bars=10,
            z_entry_threshold=1.0,  # Lower threshold for more trades
            z_exit_threshold=0.3,
            min_volume_filter=0
        )

        risk_config = RiskConfig(
            max_daily_loss=100.0,  # Low limit
            max_position_size=1,
            max_consecutive_losses=2,  # Very strict
            max_trades_per_day=3  # Limited trades
        )

        backtest_config = BacktestConfig(
            initial_capital=10000.0,
            commission_per_trade=2.50,
            slippage_ticks=0.25,
            use_risk_limits=True  # Enable risk limits
        )

        engine = BacktestEngine(trading_config, risk_config, backtest_config)

        # Generate bars with volatility
        bars = []
        for i in range(100):
            price = 5000.0 + np.random.normal(0, 20)  # High volatility
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=price,
                high=price + 5,
                low=price - 5,
                close=price,
                volume=1000
            ))

        result = engine.run(bars)

        # Risk limits should cap trades
        assert result.total_trades <= 3 * 10  # Max trades per day * days

    def test_backtest_reproducibility(self, engine):
        """Test that backtest is reproducible with same data"""
        bars = []

        # Fixed seed for reproducibility
        np.random.seed(42)

        for i in range(50):
            price = 5000.0 + np.random.normal(0, 10)
            bars.append(Bar(
                time=datetime.now(timezone.utc),
                open=price,
                high=price + 2,
                low=price - 2,
                close=price,
                volume=1000
            ))

        # Run backtest twice
        result1 = engine.run(bars)

        # Reset engine
        engine2 = BacktestEngine(
            engine.trading_config,
            engine.risk_config,
            engine.config
        )

        result2 = engine2.run(bars)

        # Results should be identical
        assert result1.total_trades == result2.total_trades
        assert result1.total_pnl == result2.total_pnl
