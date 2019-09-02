from dateutil import tz, parser
from datetime import datetime


def force_utc(dt: datetime) -> datetime:
    """
    Change a datetime to UTC, and convert naive datetimes to tz-aware UTC.

    :param dt: datetime to change to UTC
    :return: tz-aware UTC datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.tzutc())
    return dt.astimezone(tz.tzutc())


def datestring_to_utc_datetime(date_string: str) -> datetime:
    """
    Convert a date string to a tz-aware UTC datetime.

    :param date_string: A datetime as a string in almost any format.
    :return: tz-aware UTC datetime
    """
    dt = parser.parse(date_string)
    return force_utc(dt)


def datetime_to_isoformat(dt: datetime) -> str:
    """
    Convert a datetime to and iso8601 date string.

    :param dt: datetime object
    :return: iso8601 date string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.tzutc())
    return dt.isoformat()


def truncate_integer(value: int, length: int = 10) -> int:
    """
    Truncate an integer value to the desired length.

    :param value: integer to truncate
    :param length: desired length of integer
    :return: truncated integer
    """
    val_length = len(str(value))
    if val_length > length:
        diff = val_length - length
        return value // (10 ** diff)
    return value
