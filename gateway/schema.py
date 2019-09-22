from datetime import datetime

from feedsearch_crawler import FeedInfo
from marshmallow import Schema, fields, post_load, EXCLUDE, ValidationError, post_dump
from yarl import URL

from gateway.utils import remove_www


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


class CustomFeedInfo(FeedInfo):
    last_seen: datetime = None
    host: str = ""

    @property
    def is_valid(self) -> bool:
        return bool(self.url)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.url}, {self.host})"


def score_item(item: FeedInfo, original_url: URL):
    score = 0

    url_str = str(item.url).lower()

    # -- Score Decrement --

    if original_url:
        host = remove_www(original_url.host)

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
