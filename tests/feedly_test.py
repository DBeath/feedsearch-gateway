from gateway.feedly import is_stale_feed
from datetime import datetime


def test_is_stale_feed():
    assert not is_stale_feed(1567207200000, datetime(2019, 7, 31))
    assert is_stale_feed(1564444800, datetime(2019, 7, 31))
    assert is_stale_feed(0, datetime(2019, 7, 31))
