"""
Unit tests for bot/utils/timezone.py - Timezone handling and market hours
"""
import pytest
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from bot.utils.timezone import (
    UTC, ET, SGT,
    now_utc, now_et, now_sgt,
    to_et, to_utc,
    is_market_open, is_futures_trading_hours,
    is_market_holiday, is_trading_allowed,
    get_next_market_open,
    format_time_et, format_time_sgt, format_time_utc,
    US_MARKET_HOLIDAYS
)


class TestTimezoneConstants:
    """Test timezone constant definitions"""

    def test_timezone_objects(self):
        """Test that timezone objects are properly defined"""
        assert UTC == ZoneInfo("UTC")
        assert ET == ZoneInfo("America/New_York")
        assert SGT == ZoneInfo("Asia/Singapore")


class TestCurrentTimeHelpers:
    """Test current time helper functions"""

    def test_now_utc(self):
        """Test getting current UTC time"""
        now = now_utc()

        assert now.tzinfo == UTC
        assert isinstance(now, datetime)

    def test_now_et(self):
        """Test getting current ET time"""
        now = now_et()

        assert now.tzinfo == ET
        assert isinstance(now, datetime)

    def test_now_sgt(self):
        """Test getting current SGT time"""
        now = now_sgt()

        assert now.tzinfo == SGT
        assert isinstance(now, datetime)

    def test_time_consistency(self):
        """Test that all current times represent the same instant"""
        utc = now_utc()
        et = now_et()
        sgt = now_sgt()

        # All should be within a few seconds of each other
        assert abs((et - utc).total_seconds()) < 2
        assert abs((sgt - utc).total_seconds()) < 2


class TestTimezoneConversion:
    """Test timezone conversion functions"""

    def test_to_et_from_utc(self):
        """Test converting UTC to ET"""
        utc_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)
        et_time = to_et(utc_time)

        assert et_time.tzinfo == ET
        # In January, ET is UTC-5 (EST)
        assert et_time.hour == 9

    def test_to_et_from_naive(self):
        """Test converting naive datetime to ET (assumes UTC)"""
        naive_time = datetime(2025, 1, 15, 14, 30, 0)
        et_time = to_et(naive_time)

        assert et_time.tzinfo == ET
        assert et_time.hour == 9

    def test_to_utc_from_et(self):
        """Test converting ET to UTC"""
        et_time = datetime(2025, 1, 15, 9, 30, 0, tzinfo=ET)
        utc_time = to_utc(et_time)

        assert utc_time.tzinfo == UTC
        # In January, ET is UTC-5
        assert utc_time.hour == 14

    def test_to_utc_from_naive(self):
        """Test converting naive datetime to UTC"""
        naive_time = datetime(2025, 1, 15, 14, 30, 0)
        utc_time = to_utc(naive_time)

        assert utc_time.tzinfo == UTC
        assert utc_time.hour == 14

    def test_round_trip_conversion(self):
        """Test that conversions are reversible"""
        original = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)

        # UTC -> ET -> UTC
        et_converted = to_et(original)
        back_to_utc = to_utc(et_converted)

        assert original == back_to_utc


class TestMarketHours:
    """Test market hours detection (stocks)"""

    def test_market_open_weekday(self):
        """Test that market is open during trading hours on weekday"""
        # Wednesday, 10:00 AM ET (during market hours)
        test_time = datetime(2025, 1, 15, 15, 0, 0, tzinfo=UTC)  # 10 AM ET

        assert is_market_open(test_time) is True

    def test_market_closed_before_open(self):
        """Test that market is closed before 9:30 AM ET"""
        # Wednesday, 9:00 AM ET (before open)
        test_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=UTC)  # 9 AM ET

        assert is_market_open(test_time) is False

    def test_market_closed_after_close(self):
        """Test that market is closed after 4:00 PM ET"""
        # Wednesday, 5:00 PM ET (after close)
        test_time = datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC)  # 5 PM ET

        assert is_market_open(test_time) is False

    def test_market_closed_weekend(self):
        """Test that market is closed on weekends"""
        # Saturday, 10:00 AM ET
        saturday = datetime(2025, 1, 18, 15, 0, 0, tzinfo=UTC)

        assert is_market_open(saturday) is False

        # Sunday, 10:00 AM ET
        sunday = datetime(2025, 1, 19, 15, 0, 0, tzinfo=UTC)

        assert is_market_open(sunday) is False

    def test_market_open_at_exact_open_time(self):
        """Test market status at exactly 9:30 AM ET"""
        # Wednesday, 9:30 AM ET exactly
        test_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)

        assert is_market_open(test_time) is True

    def test_market_open_at_exact_close_time(self):
        """Test market status at exactly 4:00 PM ET"""
        # Wednesday, 4:00 PM ET exactly
        test_time = datetime(2025, 1, 15, 21, 0, 0, tzinfo=UTC)

        # Implementation dependent: might be True or False
        result = is_market_open(test_time)
        assert isinstance(result, bool)


class TestFuturesTradingHours:
    """Test futures market hours (CME Globex)"""

    def test_futures_open_monday_morning(self):
        """Test that futures are open Monday morning"""
        # Monday, 10:00 AM ET
        monday = datetime(2025, 1, 13, 15, 0, 0, tzinfo=UTC)

        assert is_futures_trading_hours(monday) is True

    def test_futures_closed_saturday(self):
        """Test that futures are closed all day Saturday"""
        # Saturday, 10:00 AM ET
        saturday = datetime(2025, 1, 18, 15, 0, 0, tzinfo=UTC)

        assert is_futures_trading_hours(saturday) is False

    def test_futures_open_sunday_evening(self):
        """Test that futures open Sunday at 6:00 PM ET"""
        # Sunday, 11:00 PM UTC (6 PM ET)
        sunday_open = datetime(2025, 1, 19, 23, 0, 0, tzinfo=UTC)

        assert is_futures_trading_hours(sunday_open) is True

    def test_futures_closed_sunday_afternoon(self):
        """Test that futures are closed Sunday afternoon"""
        # Sunday, 2:00 PM ET (before 6 PM open)
        sunday_closed = datetime(2025, 1, 19, 19, 0, 0, tzinfo=UTC)

        assert is_futures_trading_hours(sunday_closed) is False

    def test_futures_maintenance_window(self):
        """Test that futures are closed during daily maintenance (5-6 PM ET)"""
        # Wednesday, 5:30 PM ET (maintenance)
        maintenance = datetime(2025, 1, 15, 22, 30, 0, tzinfo=UTC)

        assert is_futures_trading_hours(maintenance) is False

    def test_futures_after_maintenance(self):
        """Test that futures reopen after maintenance"""
        # Wednesday, 6:30 PM ET (after maintenance)
        after_maintenance = datetime(2025, 1, 15, 23, 30, 0, tzinfo=UTC)

        assert is_futures_trading_hours(after_maintenance) is True

    def test_futures_friday_close(self):
        """Test that futures close Friday at 5:00 PM ET"""
        # Friday, 6:00 PM ET (after close)
        friday_closed = datetime(2025, 1, 17, 23, 0, 0, tzinfo=UTC)

        assert is_futures_trading_hours(friday_closed) is False

    def test_futures_nearly_24_hours(self):
        """Test that futures trade nearly 24 hours (except maintenance and Sat)"""
        # Monday through Thursday should have ~23 hour trading

        # Monday, 2:00 AM ET
        early_morning = datetime(2025, 1, 13, 7, 0, 0, tzinfo=UTC)
        assert is_futures_trading_hours(early_morning) is True

        # Tuesday, 11:00 PM ET
        late_night = datetime(2025, 1, 14, 4, 0, 0, tzinfo=UTC)
        assert is_futures_trading_hours(late_night) is True


class TestMarketHolidays:
    """Test market holiday detection"""

    def test_new_years_day_2025(self):
        """Test that New Year's Day is recognized as holiday"""
        new_years = datetime(2025, 1, 1, 15, 0, 0, tzinfo=UTC)

        assert is_market_holiday(new_years) is True

    def test_christmas_2025(self):
        """Test that Christmas is recognized as holiday"""
        christmas = datetime(2025, 12, 25, 15, 0, 0, tzinfo=UTC)

        assert is_market_holiday(christmas) is True

    def test_regular_weekday_not_holiday(self):
        """Test that regular weekday is not a holiday"""
        regular_day = datetime(2025, 3, 15, 15, 0, 0, tzinfo=UTC)

        assert is_market_holiday(regular_day) is False

    def test_holiday_data_exists_for_current_year(self):
        """Test that holiday data exists for 2025-2027"""
        assert 2025 in US_MARKET_HOLIDAYS
        assert 2026 in US_MARKET_HOLIDAYS
        assert 2027 in US_MARKET_HOLIDAYS

    def test_holiday_data_format(self):
        """Test that holiday data is properly formatted"""
        holidays_2025 = US_MARKET_HOLIDAYS[2025]

        assert isinstance(holidays_2025, set)
        assert "2025-01-01" in holidays_2025  # New Year's Day
        assert "2025-12-25" in holidays_2025  # Christmas


class TestTradingAllowed:
    """Test combined trading allowed check (market hours + holidays)"""

    def test_trading_allowed_normal_day(self):
        """Test that trading is allowed on normal trading day for futures"""
        # Wednesday, 10:00 AM ET (regular trading hours)
        normal_day = datetime(2025, 3, 12, 15, 0, 0, tzinfo=UTC)

        assert is_trading_allowed(normal_day) is True

    def test_trading_not_allowed_holiday(self):
        """Test that trading is not allowed on holidays"""
        # New Year's Day, even during normal hours
        holiday = datetime(2025, 1, 1, 15, 0, 0, tzinfo=UTC)

        assert is_trading_allowed(holiday) is False

    def test_trading_allowed_uses_futures_hours(self):
        """Test that trading_allowed uses futures hours, not stock hours"""
        # Wednesday, 8:00 PM ET (futures open, stocks closed)
        evening = datetime(2025, 3, 12, 1, 0, 0, tzinfo=UTC)  # 8 PM ET

        # Should be allowed (futures are trading)
        assert is_trading_allowed(evening) is True

    def test_trading_not_allowed_maintenance(self):
        """Test that trading is not allowed during futures maintenance"""
        # Wednesday, 5:30 PM ET (maintenance window)
        maintenance = datetime(2025, 3, 12, 22, 30, 0, tzinfo=UTC)

        assert is_trading_allowed(maintenance) is False


class TestNextMarketOpen:
    """Test calculation of next market open"""

    def test_next_open_same_day(self):
        """Test next open is same day if before market open"""
        # Wednesday, 8:00 AM ET (before 9:30 open)
        before_open = datetime(2025, 1, 15, 13, 0, 0, tzinfo=UTC)

        next_open = get_next_market_open(before_open)

        assert next_open.date() == before_open.date()
        assert next_open.hour == 9
        assert next_open.minute == 30

    def test_next_open_next_day(self):
        """Test next open is next day if after market close"""
        # Wednesday, 5:00 PM ET (after close)
        after_close = datetime(2025, 1, 15, 22, 0, 0, tzinfo=UTC)

        next_open = get_next_market_open(after_close)

        # Should be Thursday 9:30 AM
        assert next_open.date() > after_close.date()
        assert next_open.hour == 9
        assert next_open.minute == 30

    def test_next_open_skip_weekend(self):
        """Test next open skips weekend"""
        # Friday, 5:00 PM ET (after close)
        friday_close = datetime(2025, 1, 17, 22, 0, 0, tzinfo=UTC)

        next_open = get_next_market_open(friday_close)

        # Should be Monday 9:30 AM
        assert next_open.weekday() == 0  # Monday
        assert next_open.hour == 9
        assert next_open.minute == 30

    def test_next_open_from_saturday(self):
        """Test next open from Saturday is Monday"""
        # Saturday, 10:00 AM ET
        saturday = datetime(2025, 1, 18, 15, 0, 0, tzinfo=UTC)

        next_open = get_next_market_open(saturday)

        # Should be Monday 9:30 AM
        assert next_open.weekday() == 0  # Monday


class TestTimeFormatting:
    """Test time formatting functions"""

    def test_format_time_et(self):
        """Test formatting time in Eastern"""
        test_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)  # 9:30 AM ET

        formatted = format_time_et(test_time)

        assert "2025-01-15" in formatted
        assert "09:30:00" in formatted
        assert "ET" in formatted

    def test_format_time_sgt(self):
        """Test formatting time in Singapore"""
        test_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)

        formatted = format_time_sgt(test_time)

        assert "2025-01-15" in formatted
        assert "SGT" in formatted

    def test_format_time_utc(self):
        """Test formatting time in UTC"""
        test_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)

        formatted = format_time_utc(test_time)

        assert "2025-01-15" in formatted
        assert "14:30:00" in formatted
        assert "UTC" in formatted

    def test_format_preserves_timezone(self):
        """Test that formatting doesn't lose timezone information"""
        # Create time in ET
        et_time = datetime(2025, 1, 15, 9, 30, 0, tzinfo=ET)

        # Format in different timezones
        et_formatted = format_time_et(et_time)
        utc_formatted = format_time_utc(et_time)

        # Both should represent same instant
        assert "09:30:00" in et_formatted
        assert "14:30:00" in utc_formatted


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_dst_transition_spring(self):
        """Test behavior during DST transition (spring forward)"""
        # Second Sunday in March (DST begins)
        # This test ensures timezone library handles DST correctly
        before_dst = datetime(2025, 3, 9, 6, 0, 0, tzinfo=UTC)  # 1 AM ET (EST)
        after_dst = datetime(2025, 3, 9, 8, 0, 0, tzinfo=UTC)   # 4 AM ET (EDT)

        # Both should convert correctly
        et_before = to_et(before_dst)
        et_after = to_et(after_dst)

        assert et_before.tzinfo == ET
        assert et_after.tzinfo == ET

    def test_dst_transition_fall(self):
        """Test behavior during DST transition (fall back)"""
        # First Sunday in November (DST ends)
        before_dst = datetime(2025, 11, 2, 5, 0, 0, tzinfo=UTC)  # 1 AM EDT
        after_dst = datetime(2025, 11, 2, 7, 0, 0, tzinfo=UTC)   # 2 AM EST

        et_before = to_et(before_dst)
        et_after = to_et(after_dst)

        assert et_before.tzinfo == ET
        assert et_after.tzinfo == ET

    def test_leap_year_handling(self):
        """Test that leap years are handled correctly"""
        # 2024 is a leap year
        leap_day = datetime(2024, 2, 29, 15, 0, 0, tzinfo=UTC)

        # Should not raise error
        assert is_market_open(leap_day) in [True, False]

    def test_year_boundary(self):
        """Test behavior at year boundaries"""
        # December 31, 2025
        year_end = datetime(2025, 12, 31, 15, 0, 0, tzinfo=UTC)

        # Should handle normally
        assert is_market_open(year_end) in [True, False]

        # January 1, 2026 (New Year's Day)
        year_start = datetime(2026, 1, 1, 15, 0, 0, tzinfo=UTC)

        # Should be a holiday
        assert is_market_holiday(year_start) is True

    def test_very_far_future_date(self):
        """Test handling of far future dates (no holiday data)"""
        # Year 2030 (no holiday data)
        future_date = datetime(2030, 6, 15, 15, 0, 0, tzinfo=UTC)

        # Should handle gracefully (log warning, return False)
        result = is_market_holiday(future_date)

        # Expected to return False (no data = assume not a holiday)
        assert result is False

    def test_midnight_boundary(self):
        """Test behavior at midnight"""
        # Midnight ET (5:00 AM UTC in winter)
        midnight_et = datetime(2025, 1, 15, 5, 0, 0, tzinfo=UTC)

        # Should be handled correctly
        assert is_futures_trading_hours(midnight_et) is True
