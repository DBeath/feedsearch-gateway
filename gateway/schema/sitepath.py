from datetime import datetime
from typing import List


class SitePath:
    def __init__(
        self, host: str, path: str, last_seen: datetime = None, feeds: List[str] = None
    ):
        self.host = host
        self.path = path
        self.last_seen = last_seen
        self.feeds = feeds or []

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.host == other.host
            and self.path == other.path
        )

    def __hash__(self):
        return hash(f"{self.host}{self.path}")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.host}{self.path})"
