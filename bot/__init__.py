"""
Quant Scalping Bot
==================

An automated futures scalping bot using Z-Score mean reversion strategy.

Components:
- core: Trading engine, signals, state management
- ibkr: Interactive Brokers API integration
- risk: Risk management, circuit breakers
- alerts: Telegram notifications
- persistence: Database, state persistence
- utils: Logging, timezone, validation

Quick Start:
    python -m bot.main config/config.yaml
"""

__version__ = "0.1.0"
__author__ = "Your Name"
