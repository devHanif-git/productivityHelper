"""Tests for semester week calculation and academic calendar logic."""

import pytest
from datetime import date, datetime, timedelta

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.semester_logic import (
    get_current_week,
    get_next_week,
    is_class_day,
    get_event_on_date,
    get_affected_classes,
    get_next_offday,
    format_date,
    format_time,
    parse_date,
    days_until,
    hours_until,
)


class TestParseDate:
    """Tests for date parsing."""

    def test_parse_iso_date(self):
        """Parse ISO format date string."""
        result = parse_date("2025-10-20")
        assert result == date(2025, 10, 20)

    def test_parse_iso_datetime(self):
        """Parse ISO datetime string (extracts date)."""
        result = parse_date("2025-10-20T14:30:00")
        assert result == date(2025, 10, 20)

    def test_parse_empty_string(self):
        """Empty string returns None."""
        assert parse_date("") is None

    def test_parse_none(self):
        """None returns None."""
        assert parse_date(None) is None

    def test_parse_invalid(self):
        """Invalid format returns None."""
        assert parse_date("invalid") is None


class TestGetCurrentWeek:
    """Tests for semester week calculation."""

    @pytest.fixture
    def semester_start(self):
        """Standard semester start date."""
        return date(2025, 10, 6)  # Monday, Oct 6, 2025

    @pytest.fixture
    def sample_events(self):
        """Sample academic events."""
        return [
            {
                "event_type": "holiday",
                "name": "Hari Deepavali",
                "start_date": "2025-10-20",
                "end_date": "2025-10-20",
                "affects_classes": True
            },
            {
                "event_type": "break",
                "name": "Cuti Pertengahan Semester",
                "name_en": "Mid-semester Break",
                "start_date": "2025-11-15",
                "end_date": "2025-11-23",
                "affects_classes": True
            },
            {
                "event_type": "exam",
                "name": "Peperiksaan Akhir",
                "name_en": "Final Exam",
                "start_date": "2026-01-05",
                "end_date": "2026-01-18",
                "affects_classes": True
            }
        ]

    def test_week_one(self, semester_start, sample_events):
        """First day of semester is Week 1."""
        result = get_current_week(semester_start, semester_start, sample_events)
        assert result == 1

    def test_before_semester(self, semester_start, sample_events):
        """Date before semester returns message."""
        before = semester_start - timedelta(days=7)
        result = get_current_week(before, semester_start, sample_events)
        assert result == "Before semester starts"

    def test_week_two(self, semester_start, sample_events):
        """Second week of semester."""
        week_two_date = semester_start + timedelta(days=7)
        result = get_current_week(week_two_date, semester_start, sample_events)
        assert result == 2

    def test_during_break(self, semester_start, sample_events):
        """Date during break returns break name."""
        break_date = date(2025, 11, 17)  # During mid-sem break
        result = get_current_week(break_date, semester_start, sample_events)
        assert result == "Mid-semester Break"

    def test_during_exam(self, semester_start, sample_events):
        """Date during exam returns exam name."""
        exam_date = date(2026, 1, 10)  # During final exam
        result = get_current_week(exam_date, semester_start, sample_events)
        assert result == "Final Exam"


class TestGetNextWeek:
    """Tests for next week calculation."""

    def test_next_week_from_week_one(self):
        """Next week from Week 1 is Week 2."""
        semester_start = date(2025, 10, 6)
        today = date(2025, 10, 6)
        result = get_next_week(today, semester_start, [])
        assert result == 2


class TestIsClassDay:
    """Tests for class day detection."""

    @pytest.fixture
    def sample_events(self):
        return [
            {
                "event_type": "holiday",
                "name": "Hari Deepavali",
                "start_date": "2025-10-20",
                "end_date": "2025-10-20",
                "affects_classes": True
            }
        ]

    def test_weekday_no_event(self):
        """Regular weekday is a class day."""
        result = is_class_day(date(2025, 10, 7), [])  # Tuesday
        assert result is True

    def test_saturday(self):
        """Saturday is not a class day."""
        result = is_class_day(date(2025, 10, 11), [])  # Saturday
        assert result is False

    def test_sunday(self):
        """Sunday is not a class day."""
        result = is_class_day(date(2025, 10, 12), [])  # Sunday
        assert result is False

    def test_holiday(self, sample_events):
        """Holiday is not a class day."""
        result = is_class_day(date(2025, 10, 20), sample_events)  # Deepavali
        assert result is False


class TestGetEventOnDate:
    """Tests for event lookup."""

    @pytest.fixture
    def sample_events(self):
        return [
            {
                "event_type": "holiday",
                "name": "Hari Deepavali",
                "start_date": "2025-10-20",
                "end_date": "2025-10-20",
                "affects_classes": True
            },
            {
                "event_type": "break",
                "name": "Cuti Pertengahan",
                "start_date": "2025-11-15",
                "end_date": "2025-11-23",
                "affects_classes": True
            }
        ]

    def test_single_day_event(self, sample_events):
        """Find single-day holiday."""
        result = get_event_on_date(date(2025, 10, 20), sample_events)
        assert result is not None
        assert result["name"] == "Hari Deepavali"

    def test_multi_day_event(self, sample_events):
        """Find event within multi-day range."""
        result = get_event_on_date(date(2025, 11, 17), sample_events)
        assert result is not None
        assert result["name"] == "Cuti Pertengahan"

    def test_no_event(self, sample_events):
        """No event on regular day."""
        result = get_event_on_date(date(2025, 10, 15), sample_events)
        assert result is None


class TestGetNextOffday:
    """Tests for finding next off day."""

    @pytest.fixture
    def sample_events(self):
        return [
            {
                "event_type": "holiday",
                "name": "Hari Deepavali",
                "start_date": "2025-10-20",
                "affects_classes": True
            },
            {
                "event_type": "holiday",
                "name": "Hari Krismas",
                "start_date": "2025-12-25",
                "affects_classes": True
            }
        ]

    def test_find_next_offday(self, sample_events):
        """Find next upcoming off day."""
        result = get_next_offday(date(2025, 10, 15), sample_events)
        assert result is not None
        assert result["date"] == date(2025, 10, 20)

    def test_no_upcoming_offday(self, sample_events):
        """No off days in range."""
        result = get_next_offday(date(2026, 1, 1), sample_events, days_ahead=10)
        assert result is None


class TestFormatDate:
    """Tests for date formatting."""

    def test_format_with_day(self):
        """Format with day name."""
        result = format_date(date(2025, 10, 20))  # Monday
        assert "Monday" in result
        assert "20 Oct 2025" in result

    def test_format_without_day(self):
        """Format without day name."""
        result = format_date(date(2025, 10, 20), include_day=False)
        assert "Monday" not in result
        assert "20 Oct 2025" in result


class TestFormatTime:
    """Tests for time formatting."""

    def test_format_morning(self):
        """Format morning time."""
        assert format_time("08:00") == "8AM"

    def test_format_noon(self):
        """Format noon."""
        assert format_time("12:00") == "12PM"

    def test_format_afternoon(self):
        """Format afternoon time."""
        assert format_time("14:30") == "2:30PM"

    def test_format_midnight(self):
        """Format midnight."""
        assert format_time("00:00") == "12AM"

    def test_format_invalid(self):
        """Invalid format returns original."""
        assert format_time("invalid") == "invalid"


class TestDaysUntil:
    """Tests for days calculation."""

    def test_same_day(self):
        """Same day returns 0."""
        today = date(2025, 10, 20)
        assert days_until(today, today) == 0

    def test_future_date(self):
        """Future date returns positive."""
        today = date(2025, 10, 20)
        target = date(2025, 10, 25)
        assert days_until(target, today) == 5

    def test_past_date(self):
        """Past date returns negative."""
        today = date(2025, 10, 20)
        target = date(2025, 10, 15)
        assert days_until(target, today) == -5


class TestHoursUntil:
    """Tests for hours calculation."""

    def test_same_time(self):
        """Same time returns 0."""
        now = datetime(2025, 10, 20, 14, 0)
        assert hours_until(now, now) == 0

    def test_future_time(self):
        """Future time returns positive."""
        now = datetime(2025, 10, 20, 14, 0)
        target = datetime(2025, 10, 20, 16, 0)
        assert hours_until(target, now) == 2.0

    def test_past_time(self):
        """Past time returns negative."""
        now = datetime(2025, 10, 20, 14, 0)
        target = datetime(2025, 10, 20, 12, 0)
        assert hours_until(target, now) == -2.0


class TestGetAffectedClasses:
    """Tests for affected classes lookup."""

    @pytest.fixture
    def sample_schedule(self):
        return [
            {"day_of_week": 0, "subject_code": "BITP1113", "start_time": "08:00"},
            {"day_of_week": 0, "subject_code": "BITI1213", "start_time": "10:00"},
            {"day_of_week": 1, "subject_code": "BITM1113", "start_time": "14:00"},
        ]

    @pytest.fixture
    def sample_events(self):
        return [
            {
                "event_type": "holiday",
                "name": "Holiday",
                "start_date": "2025-10-20",  # Monday
                "affects_classes": True
            }
        ]

    def test_no_event_no_affected(self, sample_schedule, sample_events):
        """Regular day has no affected classes."""
        result = get_affected_classes(date(2025, 10, 21), sample_schedule, sample_events)
        assert result == []

    def test_holiday_affects_classes(self, sample_schedule, sample_events):
        """Holiday cancels scheduled classes."""
        result = get_affected_classes(date(2025, 10, 20), sample_schedule, sample_events)
        assert len(result) == 2  # 2 Monday classes
        assert all(c["day_of_week"] == 0 for c in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
