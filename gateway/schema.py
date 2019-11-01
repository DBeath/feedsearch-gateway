from datetime import datetime

from feedsearch_crawler import FeedInfo
from marshmallow import Schema, fields, post_load, EXCLUDE, ValidationError, post_dump
from yarl import URL

from gateway.utils import remove_subdomains


class NoneString(fields.String):
    def _serialize(self, value, attr, obj, **kwargs):
        if value == "":
            return None
        return super(NoneString, self)._serialize(value, attr, obj, **kwargs)


class URLField(fields.String):
    def _serialize(self, value, attr, obj, **kwargs):
        if value == "":
            return None
        return super(URLField, self)._serialize(str(value), attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, (str, bytes)):
            raise self.make_error("invalid")
        try:
            return URL(value)
        except Exception as error:
            raise self.make_error("invalid") from error


class FeedInfoSchema(Schema):
    url = URLField()
    site_url = URLField(allow_none=True)
    title = NoneString(allow_none=True)
    description = NoneString(allow_none=True)
    site_name = NoneString(allow_none=True)
    favicon = URLField(allow_none=True)
    hubs = fields.List(NoneString(), allow_none=True)
    is_podcast = fields.Boolean(allow_none=True, default=False)
    is_push = fields.Boolean(allow_none=True, default=False)
    content_type = NoneString(allow_none=True)
    content_length = fields.Integer(allow_none=True, strict=False, default=0)
    bozo = fields.Integer(allow_none=True, strict=False, default=0)
    version = NoneString(allow_none=True)
    velocity = fields.Float(allow_none=True)
    self_url = URLField(allow_none=True)
    score = fields.Integer(allow_none=True, strict=False, default=0)
    favicon_data_uri = NoneString(allow_none=True)
    last_updated = fields.DateTime(allow_none=True)
    last_seen = fields.DateTime(allow_none=True)

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE

    @post_load
    def make_feed_info(self, data, **kwargs):
        return CustomFeedInfo(**data)


class SiteFeedSchema(Schema):
    host = fields.String()
    last_seen = fields.DateTime()
    feeds = fields.Nested(FeedInfoSchema, many=True)

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE


class DynamoDbFeedInfoSchema(FeedInfoSchema):
    PK = fields.Method("feed_primary_key")
    SK = fields.Method("feed_sort_key")
    host = fields.String()
    velocity = fields.Decimal(allow_none=True)

    def feed_primary_key(self, obj):
        if not obj.host:
            raise ValidationError("Site Host must exist.")
        return f"SITE#{obj.host}"

    def feed_sort_key(self, obj):
        if not obj.url:
            raise ValidationError("URL must exist.")
        return f"FEED#{obj.url}"

    @post_load
    def make_feed_info(self, data, **kwargs):
        return CustomFeedInfo(**data)

    @post_dump
    def remove_skip_values(self, data, **kwargs):
        return {key: value for key, value in data.items() if value is not None}


class DynamoDbSiteSchema(Schema):
    host = fields.String()
    last_seen = fields.DateTime()
    PK = fields.Method("site_primary_key")
    SK = fields.Method("site_sort_key")

    def site_primary_key(self, obj):
        if not obj.get("host"):
            raise ValidationError("Host value must exist.")
        return f"SITE#{obj.get('host')}"

    def site_sort_key(self, obj):
        if not obj.get("host"):
            raise ValidationError("Host value must exist.")
        return f"#METADATA#{obj.get('host')}"

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE


class DynamoDbSitePathSchema(Schema):
    host = fields.String()
    last_seen = fields.DateTime()
    path = fields.String(dump_only=True)
    PK = fields.Method("sitepath_primary_key")
    SK = fields.Method("sitepath_sort_key")

    def sitepath_primary_key(self, obj):
        if not obj.get("host"):
            raise ValidationError("Host value must exist.")
        return f"SITEPATH#{obj.get('host')}"

    def site_sort_key(self, obj):
        if not obj.get("path"):
            raise ValidationError("Path value must exist.")
        return f"PATH#{obj.get('path')}"

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE


class SitePath:
    def __init__(self, host: str, path: str, last_seen: datetime = None):
        self.host = host
        self.path = path
        self.last_seen = last_seen

    def dynamodb_serialize(self, last_seen: datetime):
        return {
            "PK": f"SITEPATH#{self.host}",
            "SK": f"PATH#{self.path}",
            "last_seen": last_seen,
        }

    @classmethod
    def dynamodb_deserialize(cls, obj: dict):
        host = obj.get("PK")[:9]
        path = obj.get("SK")[:5]
        last_seen = obj.get("last_seen")
        return cls(host, path, last_seen)

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


def score_item(item: FeedInfo, original_url: URL):
    score = 0

    url_str = str(item.url).lower()

    # -- Score Decrement --

    if original_url:
        host = remove_subdomains(original_url.host)

        if host not in item.url.host:
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
    if "comments" in url_str or "comments" in item.title.lower():
        score -= 15
    if "feedburner" in url_str:
        score -= 10

    # -- Score Increment --
    if item.url.scheme == "https":
        score += 10
    if item.is_push:
        score += 10
    if "index" in url_str:
        score += 30

    if any(map(url_str.count, ["/home", "/top", "/most", "/magazine"])):
        score += 10

    kw = ["atom", "rss", ".xml", "feed", "rdf"]
    for p, t in zip(range(len(kw) * 2, 0, -2), kw):
        if t in url_str:
            score += p

    item.score = score
