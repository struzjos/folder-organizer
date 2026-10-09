from datetime import date, datetime, time

import pytest

from folder_organizer.day import logical_date, parse_time

RESET = time(4, 0)


def test_before_reset_belongs_to_previous_day():
    assert logical_date(datetime(2026, 10, 10, 3, 59), RESET) == date(2026, 10, 9)


def test_at_reset_starts_new_day():
    assert logical_date(datetime(2026, 10, 10, 4, 0), RESET) == date(2026, 10, 10)


def test_after_midnight_before_reset():
    assert logical_date(datetime(2026, 10, 10, 0, 30), RESET) == date(2026, 10, 9)


def test_custom_reset_time():
    reset = time(6, 30)
    assert logical_date(datetime(2026, 10, 10, 6, 29), reset) == date(2026, 10, 9)
    assert logical_date(datetime(2026, 10, 10, 6, 30), reset) == date(2026, 10, 10)


def test_midnight_reset_is_calendar_day():
    assert logical_date(datetime(2026, 10, 10, 0, 0), time(0, 0)) == date(2026, 10, 10)


def test_month_and_year_boundaries():
    assert logical_date(datetime(2026, 11, 1, 3, 0), RESET) == date(2026, 10, 31)
    assert logical_date(datetime(2027, 1, 1, 2, 0), RESET) == date(2026, 12, 31)


@pytest.mark.parametrize("text, expected", [("04:00", time(4, 0)), ("6:30", time(6, 30)), (" 23:59 ", time(23, 59))])
def test_parse_time_valid(text, expected):
    assert parse_time(text) == expected


@pytest.mark.parametrize("value", ["4", "25:00", "04:60", "aa:bb", "", 4, None])
def test_parse_time_invalid(value):
    with pytest.raises(ValueError):
        parse_time(value)
