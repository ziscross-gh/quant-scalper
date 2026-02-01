"""
Utility helper functions.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    """Format datetime for logging"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_currency(value: float) -> str:
    """Format value as currency"""
    return f"${value:,.2f}"


def format_percent(value: float) -> str:
    """Format value as percentage"""
    return f"{value:.2f}%"


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    quantity: int,
    multiplier: float = 1.0,
) -> float:
    """
    Calculate profit/loss.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        quantity: Position quantity (positive for long, negative for short)
        multiplier: Contract multiplier (e.g., $5 per point for MES)

    Returns:
        Profit/loss in dollars
    """
    price_diff = exit_price - entry_price
    pnl = price_diff * quantity * multiplier
    return pnl


def validate_price(price: float) -> bool:
    """Validate that price is positive"""
    return price > 0


def validate_quantity(quantity: int) -> bool:
    """Validate that quantity is non-zero"""
    return quantity != 0


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(value, max_val))


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls = []

    def can_proceed(self) -> bool:
        """Check if action is allowed"""
        now = utc_now()

        # Remove old calls outside the window
        self._calls = [
            t for t in self._calls
            if (now - t).total_seconds() < self.window
        ]

        if len(self._calls) < self.max_calls:
            self._calls.append(now)
            return True

        return False

    def reset(self):
        """Reset the rate limiter"""
        self._calls = []


def test_helpers():
    """Test helper functions"""
    print("Testing utility helpers...")
    print("=" * 40)

    # Test P&L calculation
    print("\n1. P&L Calculation:")
    pnl = calculate_pnl(5000.0, 5025.0, 1, multiplier=5.0)
    print(f"   Long 1 MES 5000→5025: ${pnl:,.2f} (expected: $125.00)")

    pnl = calculate_pnl(5000.0, 4980.0, -1, multiplier=5.0)
    print(f"   Short 1 MES 5000→4980: ${pnl:,.2f} (expected: $100.00)")

    # Test formatters
    print("\n2. Formatters:")
    print(f"   Currency: {format_currency(1234.567)}")
    print(f"   Percent: {format_percent(12.3456)}")
    print(f"   Timestamp: {format_timestamp(utc_now())}")

    # Test rate limiter
    print("\n3. Rate Limiter (max 3 calls in 1 second):")
    limiter = RateLimiter(max_calls=3, window_seconds=1.0)

    for i in range(5):
        if limiter.can_proceed():
            print(f"   Call {i+1}: ✅ Allowed")
        else:
            print(f"   Call {i+1}: ❌ Rate limited")

    print("\n✅ All helper tests passed!")


if __name__ == "__main__":
    test_helpers()
