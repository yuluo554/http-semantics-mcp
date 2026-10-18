"""Time parsing: ``YYYY-MM-DDTHH:MM:SSZ`` and IMF-fixdate (data/README.md §4.4).

Both forms resolve to integer UTC seconds. Sub-second digits are truncated,
never rounded. Nothing here reads a clock.
"""

import re

from .errors import invalid_time

__all__ = ["parse_time", "ISO_FORM", "HTTP_DATE_FORM"]

ISO_FORM = "iso8601"
HTTP_DATE_FORM = "http-date"

_ISO = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z$"
)
_HTTP = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(\d{4}) (\d{2}):(\d{2}):(\d{2}) GMT$"
)

_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def _days_from_civil(year, month, day):
    """Days since 1970-01-01 for a proleptic Gregorian date (Howard Hinnant)."""
    year -= 1 if month <= 2 else 0
    era = (year if year >= 0 else year - 399) // 400
    year_of_era = year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468


def _validate(year, month, day, hour, minute, second):
    if not 1 <= month <= 12:
        return False
    lengths = (31, 29 if _leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not 1 <= day <= lengths[month - 1]:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 60


def _leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def parse_time(value, field):
    """Return ``(form, timestamp)`` or raise ``INVALID_TIME_FORMAT``."""
    if not isinstance(value, str):
        raise invalid_time(field, value)

    match = _ISO.match(value)
    if match:
        year, month, day, hour, minute, second = [int(part) for part in match.groups()[:6]]
        if not _validate(year, month, day, hour, minute, second):
            raise invalid_time(field, value)
        seconds = _days_from_civil(year, month, day) * 86400
        return ISO_FORM, seconds + hour * 3600 + minute * 60 + min(second, 59)

    match = _HTTP.match(value)
    if match:
        day_name, day, month_name, year, hour, minute, second = match.groups()
        year, day, hour, minute, second = int(year), int(day), int(hour), int(minute), int(second)
        month = _MONTHS[month_name]
        if not _validate(year, month, day, hour, minute, second):
            raise invalid_time(field, value)
        seconds = _days_from_civil(year, month, day) * 86400
        epoch = seconds + hour * 3600 + minute * 60 + min(second, 59)
        if _weekday(epoch) != day_name:
            raise invalid_time(field, value)
        return HTTP_DATE_FORM, epoch

    raise invalid_time(field, value)


_WEEKDAYS = ("Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed")


def _weekday(epoch):
    """1970-01-01 was a Thursday; ``epoch`` is in seconds."""
    return _WEEKDAYS[(epoch // 86400) % 7]
