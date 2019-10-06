from yarl import URL

from gateway.utils import (
    datetime_to_isoformat,
    datestring_to_utc_datetime,
    force_utc,
    truncate_integer,
    coerce_url,
    has_path,
)
from datetime import datetime
from dateutil import tz


def test_force_utc():
    assert force_utc(datetime(2019, 1, 1, 1, tzinfo=tz.gettz("CET"))) == datetime(
        2019, 1, 1, 0, tzinfo=tz.tzutc()
    )
    assert force_utc(datetime(2019, 1, 1)) == datetime(2019, 1, 1, tzinfo=tz.tzutc())
    assert force_utc(datetime(2019, 1, 1, tzinfo=tz.tzutc())) == datetime(
        2019, 1, 1, tzinfo=tz.tzutc()
    )


def test_datetime_to_isoformat():
    assert datetime_to_isoformat(datetime(2019, 1, 1)) == "2019-01-01T00:00:00+00:00"
    assert (
        datetime_to_isoformat(datetime(2019, 1, 1, tzinfo=tz.gettz("CET")))
        == "2019-01-01T00:00:00+01:00"
    )


def test_datestring_to_datetime():
    assert datestring_to_utc_datetime("2019-01-01") == datetime(
        2019, 1, 1, 0, 0, 0, tzinfo=tz.tzutc()
    )
    assert datestring_to_utc_datetime("2019-01-01 1:00:00+01:00") == datetime(
        2019, 1, 1, 0, 0, 0, tzinfo=tz.tzutc()
    )
    assert datestring_to_utc_datetime("Fri, 30 Aug 2019 04:00:00 -0000") == datetime(
        2019, 8, 30, 4, tzinfo=tz.tzutc()
    )
    assert datestring_to_utc_datetime("Fri, 30 Aug 2019 04:00:00 +0100") == datetime(
        2019, 8, 30, 3, tzinfo=tz.tzutc()
    )
    assert datestring_to_utc_datetime("2010-02-07T14:04:00-05:00") == datetime(
        2010, 2, 7, 19, 4, tzinfo=tz.tzutc()
    )


def test_truncate_integer():
    assert len(str(truncate_integer(10, 2))) == 2
    assert len(str(truncate_integer(10000, 3))) == 3
    assert len(str(truncate_integer(1234567890000, 10))) == 10
    assert len(str(truncate_integer(10000, 10))) == 5


def test_coerce_url():
    assert coerce_url("test.com") == URL("http://test.com")
    assert coerce_url("https://test.com") == URL("https://test.com")
    assert coerce_url(" https://test.com") == URL("https://test.com")
    assert coerce_url("test.com/path/path2") == URL("http://test.com/path/path2")

    assert coerce_url("test.com", https=True) == URL("https://test.com")
    assert coerce_url("https://test.com", https=True) == URL("https://test.com")
    assert coerce_url(" https://test.com", https=True) == URL("https://test.com")
    assert coerce_url("http://test.com", https=True) == URL("https://test.com")
    assert coerce_url("test.com/path/path2", https=True) == URL(
        "https://test.com/path/path2"
    )


def test_has_path():
    assert has_path(URL("https://test.com")) is False
    assert has_path(URL("https://test.com/")) is False
    assert has_path(URL("https://test.com/path")) is True
    assert has_path(URL("https://test.com/path/")) is True
    assert has_path(URL("https://test.com/path/path2")) is True
    assert has_path(URL("https://test.com/path?query=true")) is True
    assert has_path(URL("test.com/path")) is True
    assert has_path(URL("test.com/path/")) is True
    assert has_path(URL("test.com")) is True
    assert has_path(URL("test.com/")) is True
