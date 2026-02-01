"""
Alert integrations for the trading bot.

Note: TelegramAlertManager requires aiohttp. Import only when needed.
"""

# Lazy import to avoid dependency issues
def get_telegram_manager():
    """Get TelegramAlertManager (lazy import)"""
    from .telegram import TelegramAlertManager, TelegramConfig
    return TelegramAlertManager, TelegramConfig

__all__ = ["TelegramAlertManager", "TelegramConfig"]
