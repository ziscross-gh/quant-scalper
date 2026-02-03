"""
Test Trading Hours Fix (Task 2.2)
====================================
Tests to verify that the bot now uses CME futures hours correctly.

Test cases cover:
1. Sunday evening opening (5:00 PM CT)
2. Daily maintenance break (4:00 PM - 5:00 PM CT)
3. Friday closing (4:00 PM CT)
4. Weekend closure (Saturday)
5. Early morning trading (Monday-Thursday)
6. Late night trading (Monday-Thursday)

Created by: Kai (Developer)
Date: 2026-02-03
"""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.utils.timezone import (
    is_futures_trading_hours,
    is_trading_allowed,
    is_market_holiday,
    CT,
)


class TestSundayOpening:
    """Test Sunday 5:00 PM CT opening"""

    def test_sunday_before_open(self):
        """Sunday at 4:59 PM CT - market closed"""
        # Create Sunday at 4:59 PM CT
        test_time = datetime(2026, 2, 2, 16, 59, 0, tzinfo=CT)  # Sunday

        assert is_futures_trading_hours(test_time) is False, "Market should be closed before 5 PM Sunday"
        assert is_trading_allowed(test_time) is False

    def test_sunday_at_open(self):
        """Sunday at 5:00 PM CT - market opens"""
        test_time = datetime(2026, 2, 2, 17, 0, 0, tzinfo=CT)  # Sunday

        assert is_futures_trading_hours(test_time) is True, "Market should open at 5 PM Sunday"
        assert is_trading_allowed(test_time) is True

    def test_sunday_evening(self):
        """Sunday at 8:00 PM CT - market open"""
        test_time = datetime(2026, 2, 2, 20, 0, 0, tzinfo=CT)  # Sunday

        assert is_futures_trading_hours(test_time) is True, "Market should be open Sunday evening"
        assert is_trading_allowed(test_time) is True


class TestDailyMaintenanceBreak:
    """Test daily 4:00 PM - 5:00 PM CT maintenance break"""

    def test_before_maintenance(self):
        """At 3:59 PM CT - market open"""
        test_time = datetime(2026, 2, 3, 15, 59, 0, tzinfo=CT)  # Monday

        assert is_futures_trading_hours(test_time) is True, "Market should be open before maintenance"
        assert is_trading_allowed(test_time) is True

    def test_at_maintenance_start(self):
        """At 4:00 PM CT - maintenance starts"""
        test_time = datetime(2026, 2, 3, 16, 0, 0, tzinfo=CT)  # Monday

        assert is_futures_trading_hours(test_time) is False, "Market should be closed for maintenance"
        assert is_trading_allowed(test_time) is False

    def test_during_maintenance(self):
        """At 4:30 PM CT - in maintenance break"""
        test_time = datetime(2026, 2, 3, 16, 30, 0, tzinfo=CT)  # Monday

        assert is_futures_trading_hours(test_time) is False, "Market should be closed during maintenance"
        assert is_trading_allowed(test_time) is False

    def test_at_maintenance_end(self):
        """At 4:59 PM CT - still in maintenance"""
        test_time = datetime(2026, 2, 3, 16, 59, 0, tzinfo=CT)  # Monday

        assert is_futures_trading_hours(test_time) is False, "Market should be closed until 5 PM"
        assert is_trading_allowed(test_time) is False

    def test_after_maintenance(self):
        """At 5:00 PM CT - maintenance ends, market reopens"""
        test_time = datetime(2026, 2, 3, 17, 0, 0, tzinfo=CT)  # Monday

        assert is_futures_trading_hours(test_time) is True, "Market should reopen at 5 PM"
        assert is_trading_allowed(test_time) is True


class TestFridayClosing:
    """Test Friday 4:00 PM CT closing"""

    def test_friday_before_close(self):
        """Friday at 3:59 PM CT - market open"""
        test_time = datetime(2026, 2, 6, 15, 59, 0, tzinfo=CT)  # Friday (Feb 6, 2026)

        assert is_futures_trading_hours(test_time) is True, "Market should be open before close"
        assert is_trading_allowed(test_time) is True

    def test_friday_at_close(self):
        """Friday at 4:00 PM CT - market closes"""
        test_time = datetime(2026, 2, 6, 16, 0, 0, tzinfo=CT)  # Friday

        assert is_futures_trading_hours(test_time) is False, "Market should close at 4 PM Friday"
        assert is_trading_allowed(test_time) is False

    def test_friday_evening(self):
        """Friday at 5:00 PM CT - market closed"""
        test_time = datetime(2026, 2, 6, 17, 0, 0, tzinfo=CT)  # Friday

        assert is_futures_trading_hours(test_time) is False, "Market should remain closed Friday evening"
        assert is_trading_allowed(test_time) is False


class TestSaturdayClosure:
    """Test Saturday complete closure"""

    def test_saturday_morning(self):
        """Saturday at 10:00 AM CT - market closed"""
        test_time = datetime(2026, 2, 7, 10, 0, 0, tzinfo=CT)  # Saturday (Feb 7, 2026)

        assert is_futures_trading_hours(test_time) is False, "Saturday should be closed all day"
        assert is_trading_allowed(test_time) is False

    def test_saturday_noon(self):
        """Saturday at 12:00 PM CT - market closed"""
        test_time = datetime(2026, 2, 7, 12, 0, 0, tzinfo=CT)  # Saturday

        assert is_futures_trading_hours(test_time) is False, "Saturday should be closed all day"
        assert is_trading_allowed(test_time) is False

    def test_saturday_midnight(self):
        """Saturday at 11:59 PM CT - market closed"""
        test_time = datetime(2026, 2, 7, 23, 59, 0, tzinfo=CT)  # Saturday

        assert is_futures_trading_hours(test_time) is False, "Saturday should be closed all day"
        assert is_trading_allowed(test_time) is False


class TestEarlyMorningTrading:
    """Test early morning trading (Monday-Thursday)"""

    def test_monday_midnight(self):
        """Monday at 12:00 AM CT - market open"""
        test_time = datetime(2026, 2, 2, 0, 0, 0, tzinfo=CT)  # Monday (Feb 2, 2026)

        assert is_futures_trading_hours(test_time) is True, "Market should be open Monday midnight"
        assert is_trading_allowed(test_time) is True

    def test_tuesday_early(self):
        """Tuesday at 2:00 AM CT - market open"""
        test_time = datetime(2026, 2, 3, 2, 0, 0, tzinfo=CT)  # Tuesday

        assert is_futures_trading_hours(test_time) is True, "Market should be open early Tuesday"
        assert is_trading_allowed(test_time) is True

    def test_wednesday_early(self):
        """Wednesday at 4:00 AM CT - market open"""
        test_time = datetime(2026, 2, 4, 4, 0, 0, tzinfo=CT)  # Wednesday

        assert is_futures_trading_hours(test_time) is True, "Market should be open early Wednesday"
        assert is_trading_allowed(test_time) is True

    def test_thursday_morning(self):
        """Thursday at 9:00 AM CT - market open"""
        test_time = datetime(2026, 2, 5, 9, 0, 0, tzinfo=CT)  # Thursday

        assert is_futures_trading_hours(test_time) is True, "Market should be open Thursday morning"
        assert is_trading_allowed(test_time) is True


class TestLateNightTrading:
    """Test late night trading (Monday-Thursday)"""

    def test_monday_late(self):
        """Monday at 10:00 PM CT - market open"""
        test_time = datetime(2026, 2, 2, 22, 0, 0, tzinfo=CT)  # Monday

        assert is_futures_trading_hours(test_time) is True, "Market should be open Monday late"
        assert is_trading_allowed(test_time) is True

    def test_tuesday_late(self):
        """Tuesday at 11:00 PM CT - market open"""
        test_time = datetime(2026, 2, 3, 23, 0, 0, tzinfo=CT)  # Tuesday

        assert is_futures_trading_hours(test_time) is True, "Market should be open Tuesday late"
        assert is_trading_allowed(test_time) is True

    def test_wednesday_night(self):
        """Wednesday at 11:59 PM CT - market open"""
        test_time = datetime(2026, 2, 4, 23, 59, 0, tzinfo=CT)  # Wednesday

        assert is_futures_trading_hours(test_time) is True, "Market should be open Wednesday night"
        assert is_trading_allowed(test_time) is True


class Test2026Holidays:
    """Test 2026 CME holidays are respected"""

    def test_new_years_day(self):
        """January 1, 2026 - New Year's Day"""
        test_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=CT)  # Thursday

        assert is_market_holiday(test_time) is True, "Jan 1 should be holiday"
        assert is_trading_allowed(test_time) is False, "Trading should be blocked on holiday"

    def test_independence_day_observed(self):
        """July 3, 2026 - Independence Day observed (July 4 is Saturday)"""
        test_time = datetime(2026, 7, 3, 10, 0, 0, tzinfo=CT)  # Friday

        assert is_market_holiday(test_time) is True, "July 3 should be observed holiday"
        assert is_trading_allowed(test_time) is False, "Trading should be blocked on observed holiday"

    def test_christmas(self):
        """December 25, 2026 - Christmas"""
        test_time = datetime(2026, 12, 25, 10, 0, 0, tzinfo=CT)  # Friday

        assert is_market_holiday(test_time) is True, "Dec 25 should be holiday"
        assert is_trading_allowed(test_time) is False, "Trading should be blocked on Christmas"

    def test_non_holiday(self):
        """Regular trading day - should be allowed"""
        test_time = datetime(2026, 2, 3, 10, 0, 0, tzinfo=CT)  # Monday, Feb 3

        assert is_market_holiday(test_time) is False, "Feb 3 should not be holiday"
        assert is_trading_allowed(test_time) is True, "Trading should be allowed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
