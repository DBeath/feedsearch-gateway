from yarl import URL

from gateway.exceptions import BadRequestError
from gateway.utils import (
    datetime_to_isoformat,
    datestring_to_utc_datetime,
    force_utc,
    truncate_integer,
    coerce_url,
    has_path,
    validate_query,
)
from datetime import datetime
from dateutil import tz
import pytest


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


def test_validate_query_raises_badrequest():
    bad_queries = [
        "blah",
        "jsonfeed.org) WAITFOR DELAY '0:0:5' AND (5981=5981",
        "http://##/",
        "http://.",
        "//a",
        "http://3628126748",
        "curl%20-X%20GET%20%22https",
        "jsonfeed.org'%20UNION%20ALL%20SELECT%20NULL,NULL,NULL,NULL",
        "jsonfeed.org%20AND%20SLEEP(5)--%20JjtF",
        "jsonfeed.org)%20ORDER%20BY%201",
        "jsonfeed.org')%20AND%207639=6868%20AND%20('KskU'='KskU",
        "jsonfeed.org)%20AND%20(SELECT%204505%20FROM(SELECT%20COUNT(*),CONCAT(0x71707a6a71,(SELECT%20(ELT(4505=4505,1))),0x7178787a71,FLOOR(RAND(0)*2))x%20FROM%20INFORMATION_SCHEMA.CHARACTER_SETS%20GROUP%20BY%20x)a)%20AND%20(5178=5178",
    ]

    for query in bad_queries:
        with pytest.raises(BadRequestError):
            validate_query(query)
            print(query)


def test_validate_query():
    good_queries = [
        "test.com",
        "http://test.com",
        "http://test.com?query=test",
        "http://foo.com/blah_(wikipedia)#cite-1",
    ]

    for query in good_queries:
        assert isinstance(validate_query(query), URL)
