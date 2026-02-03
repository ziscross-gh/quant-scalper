"""
Unit tests for timezone utilities and CME futures trading hours.

Tests cover:
- Timezone conversions (UTC, ET, CT, SGT)
- CME futures trading hours (Sunday 5 PM CT - Friday 4 PM CT)
- Daily maintenance window (4-5 PM CT)
- Holiday detection (2025 and 2026)
- DST transitions
- Edge cases (weekends, holidays, maintenance)
"""
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.utils.timezone import (
    UTC, ET, CT, SGT,
    now_utc, now_et, now_ct, now_sgt,
    to_utc, to_et, to_ct,
    is_market_open,
    is_futures_trading_hours,
    is_market_holiday,
    is_trading_allowed,
    format_time_et, format_time_ct, format_time_utc, format_time_sgt,
)


class TestTimezoneConversions:
    """Test timezone conversion utilities"""
    
    def test_utc_to_et_conversion(self):
        """Test UTC to Eastern Time conversion"""
        # January (EST, UTC-5)
        utc_time = datetime(2026, 1, 15, 14, 30, 0, tzinfo=UTC)
        et_time = to_et(utc_time)
        assert et_time.hour == 9
        assert et_time.minute == 30
    
    def test_utc_to_ct_conversion(self):
        """Test UTC to Central Time conversion"""
        # January (CST, UTC-6)
        utc_time = datetime(2026, 1, 15, 14, 30, 0, tzinfo=UTC)
        ct_time = to_ct(utc_time)
        assert ct_time.hour == 8
        assert ct_time.minute == 30
    
    def test_naive_datetime_handling(self):
        """Test that naive datetimes are treated as UTC"""
        naive_dt = datetime(2026, 1, 15, 12, 0, 0)
        et_time = to_et(naive_dt)
        assert et_time.tzinfo == ET
    
    def test_dst_transition_spring(self):
        """Test DST transition in spring (2026: March 8)"""
        # Before DST: 1 AM CT = 7 AM UTC
        before_dst = datetime(2026, 3, 8, 7, 0, 0, tzinfo=UTC)
        ct_before = to_ct(before_dst)
        assert ct_before.hour == 1
        
        # After DST: 3 AM CT = 8 AM UTC (clock springs forward at 2 AM)
        after_dst = datetime(2026, 3, 8, 9, 0, 0, tzinfo=UTC)
        ct_after = to_ct(after_dst)
        assert ct_after.hour == 4
    
    def test_dst_transition_fall(self):
        """Test DST transition in fall (2026: November 1)"""
        # Before DST ends: 1 AM CT = 6 AM UTC
        before = datetime(2026, 11, 1, 6, 0, 0, tzinfo=UTC)
        ct_before = to_ct(before)
        assert ct_before.hour == 1
        
        # After DST ends: 1 AM CT = 7 AM UTC (clock falls back at 2 AM)
        after = datetime(2026, 11, 1, 8, 0, 0, tzinfo=UTC)
        ct_after = to_ct(after)
        assert ct_after.hour == 2


class TestFuturesTradingHours:
    """Test CME futures trading hours logic"""
    
    def test_sunday_before_open(self):
        """Sunday before 5 PM CT should be closed"""
        # Sunday 4:00 PM CT
        sunday_4pm = datetime(2026, 2, 8, 16, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(sunday_4pm) is False
    
    def test_sunday_at_open(self):
        """Sunday at exactly 5 PM CT should be open"""
        # Sunday 5:00 PM CT
        sunday_5pm = datetime(2026, 2, 8, 17, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(sunday_5pm) is True
    
    def test_sunday_after_open(self):
        """Sunday after 5 PM CT should be open"""
        # Sunday 8:00 PM CT
        sunday_8pm = datetime(2026, 2, 8, 20, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(sunday_8pm) is True
    
    def test_monday_morning(self):
        """Monday morning should be open"""
        # Monday 9:00 AM CT
        monday_9am = datetime(2026, 2, 9, 9, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(monday_9am) is True
    
    def test_daily_maintenance_window(self):
        """4:00-5:00 PM CT daily maintenance should be closed"""
        # Monday 4:00 PM CT (start of maintenance)
        monday_4pm = datetime(2026, 2, 9, 16, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(monday_4pm) is False
        
        # Monday 4:30 PM CT (during maintenance)
        monday_430pm = datetime(2026, 2, 9, 16, 30, 0, tzinfo=CT)
        assert is_futures_trading_hours(monday_430pm) is False
        
        # Monday 4:59 PM CT (end of maintenance)
        monday_459pm = datetime(2026, 2, 9, 16, 59, 0, tzinfo=CT)
        assert is_futures_trading_hours(monday_459pm) is False
        
        # Monday 5:00 PM CT (after maintenance)
        monday_5pm = datetime(2026, 2, 9, 17, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(monday_5pm) is True
    
    def test_tuesday_evening(self):
        """Tuesday evening after maintenance should be open"""
        # Tuesday 6:00 PM CT
        tuesday_6pm = datetime(2026, 2, 10, 18, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(tuesday_6pm) is True
    
    def test_wednesday_overnight(self):
        """Wednesday overnight hours should be open"""
        # Wednesday 2:00 AM CT
        wednesday_2am = datetime(2026, 2, 11, 2, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(wednesday_2am) is True
    
    def test_thursday_afternoon(self):
        """Thursday afternoon before maintenance should be open"""
        # Thursday 3:00 PM CT
        thursday_3pm = datetime(2026, 2, 12, 15, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(thursday_3pm) is True
    
    def test_friday_morning(self):
        """Friday morning should be open"""
        # Friday 10:00 AM CT
        friday_10am = datetime(2026, 2, 13, 10, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(friday_10am) is True
    
    def test_friday_at_close(self):
        """Friday at 4:00 PM CT (close) should be closed"""
        # Friday 4:00 PM CT
        friday_4pm = datetime(2026, 2, 13, 16, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(friday_4pm) is False
    
    def test_friday_evening(self):
        """Friday evening after close should be closed"""
        # Friday 6:00 PM CT
        friday_6pm = datetime(2026, 2, 13, 18, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(friday_6pm) is False
    
    def test_saturday_all_day(self):
        """Saturday should be closed all day"""
        # Saturday 12:00 PM CT
        saturday_noon = datetime(2026, 2, 14, 12, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(saturday_noon) is False
        
        # Saturday 11:00 PM CT
        saturday_11pm = datetime(2026, 2, 14, 23, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(saturday_11pm) is False
    
    def test_all_weekdays_maintenance(self):
        """Test maintenance window applies to all weekdays"""
        # Create datetime for each weekday at 4:30 PM CT
        for day_offset in range(5):  # Monday-Friday
            test_date = datetime(2026, 2, 9, 16, 30, 0, tzinfo=CT) + timedelta(days=day_offset)
            # Maintenance window should be closed
            assert is_futures_trading_hours(test_date) is False


class TestHolidayDetection:
    """Test market holiday detection for 2025 and 2026"""
    
    def test_2025_new_years(self):
        """Test New Year's Day 2025"""
        new_years = datetime(2025, 1, 1, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(new_years) is True
    
    def test_2025_mlk_day(self):
        """Test MLK Day 2025"""
        mlk_day = datetime(2025, 1, 20, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(mlk_day) is True
    
    def test_2025_good_friday(self):
        """Test Good Friday 2025"""
        good_friday = datetime(2025, 4, 18, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(good_friday) is True
    
    def test_2025_independence_day(self):
        """Test Independence Day 2025"""
        july_4th = datetime(2025, 7, 4, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(july_4th) is True
    
    def test_2025_christmas(self):
        """Test Christmas 2025"""
        christmas = datetime(2025, 12, 25, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(christmas) is True
    
    def test_2026_new_years(self):
        """Test New Year's Day 2026"""
        new_years = datetime(2026, 1, 1, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(new_years) is True
    
    def test_2026_mlk_day(self):
        """Test MLK Day 2026 (corrected to January 19)"""
        mlk_day = datetime(2026, 1, 19, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(mlk_day) is True
    
    def test_2026_presidents_day(self):
        """Test Presidents' Day 2026"""
        presidents_day = datetime(2026, 2, 16, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(presidents_day) is True
    
    def test_2026_good_friday(self):
        """Test Good Friday 2026"""
        good_friday = datetime(2026, 4, 3, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(good_friday) is True
    
    def test_2026_memorial_day(self):
        """Test Memorial Day 2026"""
        memorial_day = datetime(2026, 5, 25, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(memorial_day) is True
    
    def test_2026_juneteenth(self):
        """Test Juneteenth 2026"""
        juneteenth = datetime(2026, 6, 19, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(juneteenth) is True
    
    def test_2026_july_4th_observed(self):
        """Test Independence Day 2026 (observed July 3 since July 4 is Saturday)"""
        july_3rd = datetime(2026, 7, 3, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(july_3rd) is True
        
        # July 4 (Saturday) should not be marked as holiday in trading system
        july_4th = datetime(2026, 7, 4, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(july_4th) is False
    
    def test_2026_labor_day(self):
        """Test Labor Day 2026"""
        labor_day = datetime(2026, 9, 7, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(labor_day) is True
    
    def test_2026_thanksgiving(self):
        """Test Thanksgiving 2026"""
        thanksgiving = datetime(2026, 11, 26, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(thanksgiving) is True
    
    def test_2026_christmas(self):
        """Test Christmas 2026"""
        christmas = datetime(2026, 12, 25, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(christmas) is True
    
    def test_non_holiday(self):
        """Test a regular trading day"""
        regular_day = datetime(2026, 3, 15, 12, 0, 0, tzinfo=ET)
        assert is_market_holiday(regular_day) is False


class TestTradingAllowed:
    """Test the combined is_trading_allowed function"""
    
    def test_trading_allowed_weekday_open_hours(self):
        """Test trading allowed on regular weekday during open hours"""
        # Tuesday 10:00 AM CT (not a holiday, not maintenance)
        tuesday_10am = datetime(2026, 2, 10, 10, 0, 0, tzinfo=CT)
        assert is_trading_allowed(tuesday_10am, use_futures_hours=True) is True
    
    def test_trading_blocked_on_holiday(self):
        """Test trading blocked on CME holiday"""
        # Christmas 2026
        christmas = datetime(2026, 12, 25, 10, 0, 0, tzinfo=CT)
        assert is_trading_allowed(christmas, use_futures_hours=True) is False
    
    def test_trading_blocked_on_saturday(self):
        """Test trading blocked on Saturday"""
        # Saturday 12:00 PM CT
        saturday = datetime(2026, 2, 14, 12, 0, 0, tzinfo=CT)
        assert is_trading_allowed(saturday, use_futures_hours=True) is False
    
    def test_trading_blocked_during_maintenance(self):
        """Test trading blocked during daily maintenance"""
        # Wednesday 4:30 PM CT (maintenance window)
        wednesday_maintenance = datetime(2026, 2, 11, 16, 30, 0, tzinfo=CT)
        assert is_trading_allowed(wednesday_maintenance, use_futures_hours=True) is False
    
    def test_trading_allowed_sunday_evening(self):
        """Test trading allowed Sunday evening after open"""
        # Sunday 6:00 PM CT (after 5 PM open)
        sunday_evening = datetime(2026, 2, 8, 18, 0, 0, tzinfo=CT)
        assert is_trading_allowed(sunday_evening, use_futures_hours=True) is True
    
    def test_stock_hours_vs_futures_hours(self):
        """Test difference between stock and futures hours"""
        # Monday 8:00 AM ET / 7:00 AM CT (before stock market open, but futures are open)
        monday_8am_et = datetime(2026, 2, 9, 8, 0, 0, tzinfo=ET)
        
        # Futures should be open
        assert is_trading_allowed(monday_8am_et, use_futures_hours=True) is True
        
        # Stock market should be closed
        assert is_trading_allowed(monday_8am_et, use_futures_hours=False) is False


class TestFormatting:
    """Test time formatting functions"""
    
    def test_format_time_et(self):
        """Test ET time formatting"""
        dt = datetime(2026, 2, 3, 12, 30, 45, tzinfo=UTC)
        formatted = format_time_et(dt)
        assert "ET" in formatted
        assert "2026-02-03" in formatted
    
    def test_format_time_ct(self):
        """Test CT time formatting"""
        dt = datetime(2026, 2, 3, 12, 30, 45, tzinfo=UTC)
        formatted = format_time_ct(dt)
        assert "CT" in formatted
        assert "2026-02-03" in formatted
    
    def test_format_time_utc(self):
        """Test UTC time formatting"""
        dt = datetime(2026, 2, 3, 12, 30, 45, tzinfo=UTC)
        formatted = format_time_utc(dt)
        assert "UTC" in formatted
        assert "2026-02-03" in formatted
        assert "12:30:45" in formatted
    
    def test_format_time_sgt(self):
        """Test SGT time formatting"""
        dt = datetime(2026, 2, 3, 12, 30, 45, tzinfo=UTC)
        formatted = format_time_sgt(dt)
        assert "SGT" in formatted
        assert "2026-02-03" in formatted


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_midnight_transitions(self):
        """Test midnight boundary transitions"""
        # Monday 11:59:59 PM CT
        late_monday = datetime(2026, 2, 9, 23, 59, 59, tzinfo=CT)
        assert is_futures_trading_hours(late_monday) is True
        
        # Tuesday 12:00:00 AM CT (just after midnight)
        early_tuesday = datetime(2026, 2, 10, 0, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(early_tuesday) is True
    
    def test_maintenance_exact_boundaries(self):
        """Test exact boundary times for maintenance window"""
        # 3:59:59 PM CT (just before maintenance)
        before_maintenance = datetime(2026, 2, 9, 15, 59, 59, tzinfo=CT)
        assert is_futures_trading_hours(before_maintenance) is True
        
        # 4:00:00 PM CT (start of maintenance)
        start_maintenance = datetime(2026, 2, 9, 16, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(start_maintenance) is False
        
        # 5:00:00 PM CT (end of maintenance, market reopens)
        end_maintenance = datetime(2026, 2, 9, 17, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(end_maintenance) is True
    
    def test_friday_close_boundary(self):
        """Test Friday close at 4 PM CT"""
        # Friday 3:59:59 PM CT (just before close)
        before_close = datetime(2026, 2, 13, 15, 59, 59, tzinfo=CT)
        assert is_futures_trading_hours(before_close) is True
        
        # Friday 4:00:00 PM CT (market closes)
        at_close = datetime(2026, 2, 13, 16, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(at_close) is False
    
    def test_sunday_open_boundary(self):
        """Test Sunday open at 5 PM CT"""
        # Sunday 4:59:59 PM CT (just before open)
        before_open = datetime(2026, 2, 8, 16, 59, 59, tzinfo=CT)
        assert is_futures_trading_hours(before_open) is False
        
        # Sunday 5:00:00 PM CT (market opens)
        at_open = datetime(2026, 2, 8, 17, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(at_open) is True
    
    def test_week_wraparound(self):
        """Test trading hours across week boundaries"""
        # Friday 11:00 PM CT (after close, before weekend)
        friday_night = datetime(2026, 2, 13, 23, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(friday_night) is False
        
        # Saturday 3:00 PM CT (weekend)
        saturday = datetime(2026, 2, 14, 15, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(saturday) is False
        
        # Sunday 4:00 PM CT (before open)
        sunday_before = datetime(2026, 2, 15, 16, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(sunday_before) is False
        
        # Sunday 6:00 PM CT (after open)
        sunday_after = datetime(2026, 2, 15, 18, 0, 0, tzinfo=CT)
        assert is_futures_trading_hours(sunday_after) is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
