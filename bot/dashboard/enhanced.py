# Enhanced dashboard with Chart.js
from bot.dashboard.api import app, get_bot_status, get_positions, get_trades, get_pnl_metrics, get_backtest_runs
from fastapi import FastAPI

# Re-export everything
__all__ = [
    "app",
    "get_bot_status",
    "get_positions",
    "get_trades",
    "get_pnl_metrics",
    "get_backtest_runs",
]
