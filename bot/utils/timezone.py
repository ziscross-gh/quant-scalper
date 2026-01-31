"""
Timezone handling utilities for trading hours.

Handles conversion between:
- UTC (internal storage)
- US Eastern (market hours)
- Singapore (local display)
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Optional

# Common timezones
UTC = ZoneInfo("UTC")
ET = ZoneInfo("America/New_York")  # US Eastern (handles DST)
SGT = ZoneInfo("Asia/Singapore")


def now_utc() -> datetime:
    """Get current time in UTC"""
    return datetime.now(UTC)


def now_et() -> datetime:
    """Get current time in US Eastern"""
    return datetime.now(ET)


def now_sgt() -> datetime:
    """Get current time in Singapore"""
    return datetime.now(SGT)


def to_et(dt: datetime) -> datetime:
    """Convert any datetime to US Eastern"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ET)


def to_utc(dt: datetime) -> datetime:
    """Convert any datetime to UTC"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def is_market_open(
    current_time: Optional[datetime] = None,
    market_open: time = time(9, 30),
    market_close: time = time(16, 0),
) -> bool:
    """
    Check if US stock market is open.
    
    Default hours: 9:30 AM - 4:00 PM ET, Mon-Fri
    
    Note: This does not account for US market holidays.
    For production, integrate with a holiday calendar.
    
    Args:
        current_time: Time to check (defaults to now)
        market_open: Market open time (default 9:30 AM ET)
        market_close: Market close time (default 4:00 PM ET)
    
    Returns:
        True if market is open
    """
    if current_time is None:
        current_time = now_et()
    else:
        current_time = to_et(current_time)
    
    # Check weekday (Monday = 0, Sunday = 6)
    if current_time.weekday() >= 5:
        return False
    
    # Check time
    current_time_only = current_time.time()
    return market_open <= current_time_only <= market_close


def is_futures_trading_hours(current_time: Optional[datetime] = None) -> bool:
    """
    Check if CME futures market is open.
    
    CME Globex hours (for equity index futures like MES):
    - Sunday 6:00 PM - Friday 5:00 PM ET
    - With daily maintenance break: 5:00 PM - 6:00 PM ET
    
    Args:
        current_time: Time to check (defaults to now)
    
    Returns:
        True if futures market is open
    """
    if current_time is None:
        current_time = now_et()
    else:
        current_time = to_et(current_time)
    
    weekday = current_time.weekday()
    hour = current_time.hour
    minute = current_time.minute
    
    # Daily maintenance: 5:00 PM - 6:00 PM ET
    if hour == 17 or (hour == 18 and minute == 0):
        return False
    
    # Saturday: Closed all day
    if weekday == 5:
        return False
    
    # Sunday: Opens at 6:00 PM ET
    if weekday == 6:
        return hour >= 18
    
    # Friday: Closes at 5:00 PM ET
    if weekday == 4:
        return hour < 17
    
    # Monday-Thursday: Open except maintenance
    return True


def get_next_market_open(current_time: Optional[datetime] = None) -> datetime:
    """
    Get the next time the market opens.
    
    Args:
        current_time: Starting time (defaults to now)
    
    Returns:
        datetime of next market open in ET
    """
    from datetime import timedelta
    
    if current_time is None:
        current_time = now_et()
    else:
        current_time = to_et(current_time)
    
    # Start from today at 9:30 AM
    open_time = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
    
    # If today's open hasn't passed, check if it's a weekday
    if current_time < open_time and current_time.weekday() < 5:
        return open_time
    
    # Otherwise, find next weekday
    days_ahead = 1
    while True:
        next_open = open_time + timedelta(days=days_ahead)
        if next_open.weekday() < 5:
            return next_open
        days_ahead += 1
        if days_ahead > 7:
            break
    
    return open_time + timedelta(days=1)


def format_time_et(dt: datetime) -> str:
    """Format datetime in US Eastern for display"""
    et_time = to_et(dt)
    return et_time.strftime("%Y-%m-%d %H:%M:%S ET")


def format_time_sgt(dt: datetime) -> str:
    """Format datetime in Singapore time for display"""
    sgt_time = dt.astimezone(SGT)
    return sgt_time.strftime("%Y-%m-%d %H:%M:%S SGT")


def format_time_utc(dt: datetime) -> str:
    """Format datetime in UTC for display"""
    utc_time = to_utc(dt)
    return utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")


# Market holiday dates (US)
# TODO: Load from external source or update annually
US_MARKET_HOLIDAYS_2025 = {
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # MLK Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
}


def is_market_holiday(dt: Optional[datetime] = None) -> bool:
    """
    Check if the given date is a US market holiday.
    
    Args:
        dt: Date to check (defaults to today)
    
    Returns:
        True if it's a market holiday
    """
    if dt is None:
        dt = now_et()
    else:
        dt = to_et(dt)
    
    date_str = dt.strftime("%Y-%m-%d")
    return date_str in US_MARKET_HOLIDAYS_2025


def is_trading_allowed(current_time: Optional[datetime] = None) -> bool:
    """
    Combined check: market open AND not a holiday.
    
    This is the main function to use before trading.
    """
    if current_time is None:
        current_time = now_et()
    
    if is_market_holiday(current_time):
        return False
    
    return is_market_open(current_time)


# Self-test
if __name__ == "__main__":
    print(f"Current time (UTC): {format_time_utc(now_utc())}")
    print(f"Current time (ET):  {format_time_et(now_utc())}")
    print(f"Current time (SGT): {format_time_sgt(now_utc())}")
    print()
    print(f"Market open (stocks): {is_market_open()}")
    print(f"Futures trading hours: {is_futures_trading_hours()}")
    print(f"Is holiday: {is_market_holiday()}")
    print(f"Trading allowed: {is_trading_allowed()}")
    print()
    print(f"Next market open: {format_time_et(get_next_market_open())}")
