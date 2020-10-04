from datetime import datetime

from feedsearch_crawler import FeedInfo


class CustomFeedInfo(FeedInfo):
    last_seen: datetime = None
    host: str = ""

    @property
    def is_valid(self) -> bool:
        return bool(self.url)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.url}, {self.host})"

    def merge(self, other):
        """
        Merge missing data from a matching feed that may not have been fetched on this crawl.

        :param other: An other CustomFeedInfo or FeedInfo
        :return: None
        """
        if not isinstance(other, (self.__class__, FeedInfo)):
            return
        if not self.favicon and other.favicon:
            self.favicon = other.favicon
        if not self.favicon_data_uri and other.favicon_data_uri:
            if self.favicon == other.favicon:
                self.favicon_data_uri = other.favicon_data_uri
        if not self.site_url and other.site_url:
            self.site_url = other.site_url
        if not self.site_name and other.site_name:
            self.site_name = other.site_name

    @classmethod
    def upgrade_feedinfo(cls, info: FeedInfo) -> None:
        """
        Update FeedInfo object to CustomFeedInfo.

        :param info: FeedInfo object
        """
        info.__class__ = cls


def score_item(item: FeedInfo, query_host: str):
    score = 0

    url_str = str(item.url).lower()

    # -- Score Decrement --

    if query_host and query_host not in item.url.host:
        score -= 20

    # Decrement the score by every extra path in the url
    parts_len = len(item.url.parts)
    if parts_len > 2:
        score -= (parts_len - 2) * 2

    if item.bozo:
        score -= 20
    if not item.description:
        score -= 10
    if "georss" in url_str:
        score -= 10
    if "alt" in url_str:
        score -= 7
    if "feedburner" in url_str:
        score -= 10

    # -- Score Increment --
    if item.url.scheme == "https":
        score += 10
    if item.is_push:
        score += 10
    if "index" in url_str:
        score += 30

    if "comments" in url_str or "comments" in item.title.lower():
        score -= 15
    else:
        score += int(item.velocity)

    if any(map(url_str.count, ["/home", "/top", "/most", "/magazine"])):
        score += 10

    kw = ["atom", "rss", ".xml", "feed", "rdf"]
    for p, t in zip(range(len(kw) * 2, 0, -2), kw):
        if t in url_str:
            score += p

    item.score = score
