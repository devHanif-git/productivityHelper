"""Tests for AI image parsing with mocked responses."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.image_parser import (
    parse_academic_calendar,
    parse_timetable,
    parse_assignment_image,
    detect_image_type,
)


# Sample mock responses from Gemini
MOCK_CALENDAR_RESPONSE = json.dumps([
    {
        "type": "lecture_period",
        "name": "Kuliah Semester I Bahagian Pertama",
        "name_en": "Lecture Period Part 1",
        "start": "2025-10-06",
        "end": "2025-11-14",
        "affects_classes": False
    },
    {
        "type": "holiday",
        "name": "Hari Deepavali",
        "name_en": "Deepavali",
        "start": "2025-10-20",
        "end": "2025-10-20",
        "affects_classes": True
    },
    {
        "type": "break",
        "name": "Cuti Pertengahan Semester",
        "name_en": "Mid-semester Break",
        "start": "2025-11-15",
        "end": "2025-11-23",
        "affects_classes": True
    }
])

MOCK_TIMETABLE_RESPONSE = json.dumps([
    {
        "day": "Monday",
        "start": "08:00",
        "end": "10:00",
        "subject_code": "BITP 1113",
        "subject_name": "Programming Fundamentals",
        "class_type": "LEC",
        "room": "BK13",
        "lecturer": "DR ZAHRIAH"
    },
    {
        "day": "Monday",
        "start": "10:00",
        "end": "12:00",
        "subject_code": "BITI 1213",
        "subject_name": "Database Systems",
        "class_type": "LAB",
        "room": "MAKMAL 1",
        "lecturer": "DR YOGAN"
    }
])

MOCK_ASSIGNMENT_RESPONSE = json.dumps({
    "title": "Individual Assignment Report",
    "subject_code": "BITP1113",
    "subject_name": "Programming Fundamentals",
    "due_date": "2025-10-25",
    "due_time": "17:00",
    "requirements": ["Cover page", "10-15 pages", "APA format"]
})


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client."""
    with patch('ai.image_parser.get_gemini_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestDetectImageType:
    """Tests for image type detection."""

    @pytest.mark.asyncio
    async def test_detect_calendar(self, mock_gemini_client):
        """Detect academic calendar image."""
        mock_gemini_client.send_image = AsyncMock(return_value="calendar")

        result = await detect_image_type(b"fake_image_bytes")
        assert result == "calendar"

    @pytest.mark.asyncio
    async def test_detect_timetable(self, mock_gemini_client):
        """Detect timetable image."""
        mock_gemini_client.send_image = AsyncMock(return_value="timetable")

        result = await detect_image_type(b"fake_image_bytes")
        assert result == "timetable"

    @pytest.mark.asyncio
    async def test_detect_assignment(self, mock_gemini_client):
        """Detect assignment sheet image."""
        mock_gemini_client.send_image = AsyncMock(return_value="assignment")

        result = await detect_image_type(b"fake_image_bytes")
        assert result == "assignment"

    @pytest.mark.asyncio
    async def test_detect_unknown(self, mock_gemini_client):
        """Unknown image type."""
        mock_gemini_client.send_image = AsyncMock(return_value="unknown content")

        result = await detect_image_type(b"fake_image_bytes")
        assert result == "unknown"

    @pytest.mark.asyncio
    async def test_detect_failure(self, mock_gemini_client):
        """Handle API failure gracefully."""
        mock_gemini_client.send_image = AsyncMock(return_value=None)

        result = await detect_image_type(b"fake_image_bytes")
        assert result == "unknown"


class TestParseAcademicCalendar:
    """Tests for academic calendar parsing."""

    @pytest.mark.asyncio
    async def test_parse_valid_calendar(self, mock_gemini_client):
        """Parse valid calendar image."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=MOCK_CALENDAR_RESPONSE)

        events = await parse_academic_calendar(b"fake_image_bytes")

        assert events is not None
        assert len(events) == 3
        assert events[0]["type"] == "lecture_period"
        assert events[1]["type"] == "holiday"
        assert events[2]["type"] == "break"

    @pytest.mark.asyncio
    async def test_parse_extracts_english_names(self, mock_gemini_client):
        """Calendar parsing includes English translations."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=MOCK_CALENDAR_RESPONSE)

        events = await parse_academic_calendar(b"fake_image_bytes")

        holiday = events[1]
        assert holiday.get("name_en") == "Deepavali"

    @pytest.mark.asyncio
    async def test_parse_failure_returns_empty(self, mock_gemini_client):
        """API failure returns empty list."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=None)

        events = await parse_academic_calendar(b"fake_image_bytes")
        assert events == []

    @pytest.mark.asyncio
    async def test_parse_invalid_json_returns_empty(self, mock_gemini_client):
        """Invalid JSON returns empty list."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value="not valid json")

        events = await parse_academic_calendar(b"fake_image_bytes")
        assert events == []


class TestParseTimetable:
    """Tests for timetable parsing."""

    @pytest.mark.asyncio
    async def test_parse_valid_timetable(self, mock_gemini_client):
        """Parse valid timetable image."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=MOCK_TIMETABLE_RESPONSE)

        slots = await parse_timetable(b"fake_image_bytes")

        assert slots is not None
        assert len(slots) == 2
        assert slots[0]["subject_code"] == "BITP 1113"
        assert slots[1]["class_type"] == "LAB"

    @pytest.mark.asyncio
    async def test_parse_includes_lecturer(self, mock_gemini_client):
        """Timetable includes lecturer names."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=MOCK_TIMETABLE_RESPONSE)

        slots = await parse_timetable(b"fake_image_bytes")

        assert slots[0]["lecturer"] == "DR ZAHRIAH"
        assert slots[1]["lecturer"] == "DR YOGAN"

    @pytest.mark.asyncio
    async def test_parse_failure_returns_empty(self, mock_gemini_client):
        """API failure returns empty list."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=None)

        slots = await parse_timetable(b"fake_image_bytes")
        assert slots == []


class TestParseAssignmentImage:
    """Tests for assignment sheet parsing."""

    @pytest.mark.asyncio
    async def test_parse_valid_assignment(self, mock_gemini_client):
        """Parse valid assignment sheet."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=MOCK_ASSIGNMENT_RESPONSE)

        details = await parse_assignment_image(b"fake_image_bytes")

        assert details is not None
        assert details["title"] == "Individual Assignment Report"
        assert details["subject_code"] == "BITP1113"
        assert details["due_date"] == "2025-10-25"
        assert details["due_time"] == "17:00"

    @pytest.mark.asyncio
    async def test_parse_includes_requirements(self, mock_gemini_client):
        """Assignment parsing includes requirements."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=MOCK_ASSIGNMENT_RESPONSE)

        details = await parse_assignment_image(b"fake_image_bytes")

        assert "requirements" in details
        assert len(details["requirements"]) == 3

    @pytest.mark.asyncio
    async def test_parse_failure_returns_none(self, mock_gemini_client):
        """API failure returns None."""
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=None)

        details = await parse_assignment_image(b"fake_image_bytes")
        assert details is None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_image_bytes(self, mock_gemini_client):
        """Handle empty image bytes."""
        mock_gemini_client.send_image = AsyncMock(return_value="unknown")

        result = await detect_image_type(b"")
        # Should still call API and handle response
        assert result in ["unknown", "calendar", "timetable", "assignment"]

    @pytest.mark.asyncio
    async def test_json_with_extra_text(self, mock_gemini_client):
        """Handle JSON wrapped in extra text."""
        # Sometimes AI returns JSON with markdown code blocks
        response = "```json\n" + MOCK_CALENDAR_RESPONSE + "\n```"
        mock_gemini_client.send_image_with_json = AsyncMock(return_value=response)

        events = await parse_academic_calendar(b"fake_image_bytes")
        # Should handle or return empty
        assert isinstance(events, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
