import re
from datetime import datetime
from typing import Union

from dateutil import tz, parser
from yarl import URL


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


def remove_subdomains(host: str) -> str:
    """
    Remove certain subdomains from URL host strings.

    Subdomain should only be removed if the host has at least 3 domain parts.
    Otherwise an invalid host might be returned.

    :param host: URL host without scheme or path. e.g. www.test.com
    :return: URL host string.
    """
    split = host.split(".")
    if len(split) > 2:
        host = re.sub(
            r"^(feeds?|www|rss|api)\.", "", host, count=1, flags=re.IGNORECASE
        )
    return host


def remove_scheme(url: Union[URL, str]) -> str:
    """
    Remove the scheme from a URL.

    :param url: URL as string or URL object.
    :return: URL as string without scheme.
    """
    if isinstance(url, URL):
        url = str(url)
    return re.sub(r"^[a-z]{2,5}://", "", url.strip(), count=1, flags=re.IGNORECASE)


def coerce_url(url: Union[URL, str], https: bool = False) -> URL:
    """
    Coerce URL to valid format

    :param url: URL
    :param https: Force https if no scheme in url
    :return: str
    """
    if isinstance(url, str):
        url = URL(url.strip())

    scheme = "https" if https else "http"

    if not url.is_absolute():
        url_string = str(url)
        split = url_string.split("/", 1)
        url = URL.build(scheme=scheme, host=split[0])
        if len(split) > 1:
            url = url.with_path(split[1])
    elif url.scheme == "http" and https:
        url = url.with_scheme(scheme)

    return url


def has_path(url: URL) -> bool:
    """
    Return True if the URL has a path component.

    :param url: URL
    :return: bool
    """
    return bool(url.path.strip("/"))
