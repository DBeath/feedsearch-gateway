import re
from datetime import datetime
from typing import Union

from dateutil import tz, parser
from yarl import URL
from validators.url import url as url_validator
from validators import ValidationFailure
from gateway.exceptions import BadRequestError

subdomain_regex = re.compile(r"^(feeds?|www|rss|api)\.", re.IGNORECASE)
scheme_regex = re.compile(r"^[a-z]{2,5}://", re.IGNORECASE)

# https://mathiasbynens.be/demo/url-regex

valid_url_regex = re.compile(
    r"^((?:https?|feed)://)?[\w.-]{2,255}(?:\.[\w.-]{2,255}){1,12}[\w\-._~:/?#[\]@!$&'()*+,;=]+$",
    re.IGNORECASE,
)

basic_url_regex = re.compile(r"[a-z0-9]{2,}\.[a-z0-9]{2,}", re.IGNORECASE)

diegoperini_url_regex = re.compile(
    r"^(?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?!10(?:\.\d{1,3}){3})(?!127(?:\.\d{1,3}){3})(?!169\.254(?:\.\d{1,3}){2})(?!192\.168(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?\$_iuS",
    re.IGNORECASE,
)


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
        host = subdomain_regex.sub("", host, count=1)
    return host


def remove_scheme(url: Union[URL, str]) -> str:
    """
    Remove the scheme from a URL.

    :param url: URL as string or URL object.
    :return: URL as string without scheme.
    """
    if isinstance(url, URL):
        url = str(url)
    return scheme_regex.sub("", url.strip(), count=1)


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


def validate_query(query: str) -> URL:
    """
    Validates the query string as a URL, and returns the coerced URL.
    Raises a BadRequestError if the query string is not a valid URL.

    :param query: url query string
    :return: URL
    """
    if not query:
        raise BadRequestError("No URL in Request.")

    if not valid_url_regex.match(query):
        raise BadRequestError(
            f"Invalid URL: '{query}' is not supported as a searchable URL."
        )

    try:
        url = coerce_url(query)
        url.origin()
    except (ValueError, AttributeError) as e:
        raise BadRequestError(f"Invalid URL: Unable to parse '{query}' as a URL.")

    try:
        url_validator(str(url))
    except ValidationFailure:
        raise BadRequestError(f"Invalid URL: Unable to parse '{query}' as a URL.")

    return url
