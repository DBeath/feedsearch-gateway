from datetime import datetime
from typing import List, Dict

from gateway.schema.customfeedinfo import CustomFeedInfo


class SiteHost:
    def __init__(
        self,
        host: str,
        last_seen: datetime = None,
        feeds: Dict[str, CustomFeedInfo] = None,
    ):
        self.host = host
        self.last_seen = last_seen
        self.feeds = feeds or {}

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.host == self.host

    def __hash__(self):
        return hash(f"{self.host}")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.host})"

    def load_feeds(self, feeds: List[CustomFeedInfo]) -> None:
        self.feeds = {str(feed.url): feed for feed in feeds}
