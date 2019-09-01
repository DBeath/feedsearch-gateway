from gateway.feedly import is_stale_feed, truncate_integer
from datetime import datetime


def test_truncate_integer():
    assert len(str(truncate_integer(10, 2))) == 2
    assert len(str(truncate_integer(10000, 3))) == 3
    assert len(str(truncate_integer(1234567890000, 10))) == 10
    assert len(str(truncate_integer(10000, 10))) == 5


def test_is_stale_feed():
    assert not is_stale_feed(1567207200000, datetime(2019, 7, 31))
    assert is_stale_feed(1564444800, datetime(2019, 7, 31))
    assert is_stale_feed(0, datetime(2019, 7, 31))
