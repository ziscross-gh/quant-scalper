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
CT = ZoneInfo("America/Chicago")  # US Central (handles DST) - CME futures use CT
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


def now_ct() -> datetime:
    """Get current time in US Central (CME time)"""
    return datetime.now(CT)


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


def to_ct(dt: datetime) -> datetime:
    """Convert any datetime to US Central (CME time)"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(CT)


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
    - Sunday 5:00 PM CT through Friday 4:00 PM CT
    - Daily maintenance break: 4:00 PM - 5:00 PM CT (every day)
    
    Trading Schedule (Central Time):
    - Sunday:    5:00 PM - 4:00 PM (Monday)
    - Monday:    5:00 PM - 4:00 PM (Tuesday) [after daily break]
    - Tuesday:   5:00 PM - 4:00 PM (Wednesday) [after daily break]
    - Wednesday: 5:00 PM - 4:00 PM (Thursday) [after daily break]
    - Thursday:  5:00 PM - 4:00 PM (Friday) [after daily break]
    - Friday:    5:00 PM - 4:00 PM (Saturday, then CLOSED)
    - Saturday:  CLOSED all day
    
    Args:
        current_time: Time to check (defaults to now)
    
    Returns:
        True if futures market is open
    """
    if current_time is None:
        current_time = now_ct()
    else:
        current_time = to_ct(current_time)
    
    weekday = current_time.weekday()  # Monday=0, Sunday=6
    hour = current_time.hour
    minute = current_time.minute
    time_minutes = hour * 60 + minute  # Convert to minutes for easier comparison
    
    # Daily maintenance break: 4:00 PM - 5:00 PM CT (16:00 - 17:00)
    # This is 960-1020 minutes from midnight
    if 960 <= time_minutes < 1020:  # 16:00 - 17:00
        return False
    
    # Saturday: CLOSED all day
    if weekday == 5:
        return False
    
    # Sunday: Opens at 5:00 PM CT (17:00)
    if weekday == 6:
        return time_minutes >= 1020  # >= 17:00
    
    # Friday: Closes at 4:00 PM CT (16:00)
    # But need to handle the maintenance window properly
    # Friday trading: midnight - 4:00 PM, then CLOSED
    if weekday == 4:
        return time_minutes < 960  # < 16:00 (before maintenance)
    
    # Monday-Thursday: Open 24 hours except daily maintenance (4-5 PM)
    # Already handled maintenance window above, so return True
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


def format_time_ct(dt: datetime) -> str:
    """Format datetime in US Central (CME time) for display"""
    ct_time = to_ct(dt)
    return ct_time.strftime("%Y-%m-%d %H:%M:%S CT")


# Market holiday dates (US/CME)
# ================================
# Source: CME Group official calendar
# https://www.cmegroup.com/tools-information/holiday-calendar.html
#
# Trading Calendar Rules:
# - When a holiday falls on Saturday, markets are closed Friday before
# - When a holiday falls on Sunday, markets are closed Monday after
# - Good Friday is always observed
# - Juneteenth (June 19) observed since 2021
#
# TODO: Load from external source or update annually

US_MARKET_HOLIDAYS_2025 = {
    "2025-01-01",  # New Year's Day (Wednesday)
    "2025-01-20",  # MLK Day (3rd Monday in January)
    "2025-02-17",  # Presidents Day (3rd Monday in February)
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day (last Monday in May)
    "2025-06-19",  # Juneteenth (Thursday)
    "2025-07-04",  # Independence Day (Friday)
    "2025-09-01",  # Labor Day (1st Monday in September)
    "2025-11-27",  # Thanksgiving (4th Thursday in November)
    "2025-12-25",  # Christmas (Thursday)
}

# CME holidays for 2026
# ==================
# All dates verified against US holiday calendar rules:
# - New Year's Day: January 1, 2026 (Thursday)
# - MLK Day: 3rd Monday in January = January 19, 2026
# - Presidents' Day: 3rd Monday in February = February 16, 2026
# - Good Friday: April 3, 2026 (Easter is April 5)
# - Memorial Day: Last Monday in May = May 25, 2026
# - Juneteenth: June 19, 2026 (Friday)
# - Independence Day: July 4, 2026 is Saturday, observed Friday July 3
# - Labor Day: 1st Monday in September = September 7, 2026
# - Thanksgiving: 4th Thursday in November = November 26, 2026
# - Christmas: December 25, 2026 (Friday)
#
# Last Updated: 2026-02-03 by Kai (Developer)
# Verified: All dates calculated programmatically

US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day (Thursday)
    "2026-01-19",  # Martin Luther King Jr. Day (3rd Monday in January)
    "2026-02-16",  # Presidents' Day (3rd Monday in February)
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day (last Monday in May)
    "2026-06-19",  # Juneteenth (Friday)
    "2026-07-03",  # Independence Day observed (Friday, July 4 is Saturday)
    "2026-09-07",  # Labor Day (1st Monday in September)
    "2026-11-26",  # Thanksgiving (4th Thursday in November)
    "2026-12-25",  # Christmas (Friday)
}

# Combined holidays dictionary for easy lookup
US_MARKET_HOLIDAYS = US_MARKET_HOLIDAYS_2025 | US_MARKET_HOLIDAYS_2026


def is_market_holiday(dt: Optional[datetime] = None) -> bool:
    """
    Check if the given date is a US/CME market holiday.
    
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
    return date_str in US_MARKET_HOLIDAYS


def is_trading_allowed(current_time: Optional[datetime] = None, use_futures_hours: bool = True) -> bool:
    """
    Combined check: market open AND not a holiday.
    
    This is the main function to use before trading.
    
    Args:
        current_time: Time to check (defaults to now)
        use_futures_hours: If True, uses CME futures hours (default).
                          If False, uses stock market hours (9:30 AM - 4 PM ET).
    
    Returns:
        True if trading is allowed
    """
    if current_time is None:
        current_time = now_et()
    
    if is_market_holiday(current_time):
        return False
    
    if use_futures_hours:
        return is_futures_trading_hours(current_time)
    else:
        return is_market_open(current_time)


# Self-test
if __name__ == "__main__":
    print("=" * 60)
    print("TIMEZONE UTILITY - STATUS CHECK")
    print("=" * 60)
    print()
    print(f"Current time (UTC): {format_time_utc(now_utc())}")
    print(f"Current time (ET):  {format_time_et(now_utc())}")
    print(f"Current time (CT):  {format_time_ct(now_utc())} [CME Futures]")
    print(f"Current time (SGT): {format_time_sgt(now_utc())}")
    print()
    print("-" * 60)
    print("MARKET STATUS")
    print("-" * 60)
    print(f"Stock market open (9:30 AM - 4 PM ET): {is_market_open()}")
    print(f"CME futures trading hours (Sun 5 PM - Fri 4 PM CT): {is_futures_trading_hours()}")
    print(f"Is holiday (CME closed): {is_market_holiday()}")
    print(f"Trading allowed (futures + holiday check): {is_trading_allowed()}")
    print()
    print("-" * 60)
    print("NEXT EVENTS")
    print("-" * 60)
    print(f"Next stock market open: {format_time_et(get_next_market_open())}")
    print()
    print("=" * 60)
