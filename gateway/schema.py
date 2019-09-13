from datetime import datetime

from feedsearch_crawler import FeedInfo
from marshmallow import Schema, fields, post_load, EXCLUDE, ValidationError, pre_load


class FeedInfoSchema(Schema):
    url = fields.Url()
    site_url = fields.String(allow_none=True)
    title = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    site_name = fields.String(allow_none=True)
    favicon = fields.String(allow_none=True)
    hubs = fields.List(fields.String(), allow_none=True)
    is_push = fields.Boolean(allow_none=True)
    content_type = fields.String(allow_none=True)
    content_length = fields.Integer(allow_none=True)
    bozo = fields.Integer(allow_none=True)
    version = fields.String(allow_none=True)
    self_url = fields.String(allow_none=True)
    score = fields.Integer(allow_none=True)
    favicon_data_uri = fields.String(allow_none=True)
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

    def feed_primary_key(self, obj):
        if not obj.host:
            raise ValidationError("Site Host must exist.")
        return f"SITE#{obj.host}"

    def feed_sort_key(self, obj):
        if not obj.url:
            raise ValidationError("URL must exist.")
        return f"Feed#{obj.url}"

    @post_load
    def make_feed_info(self, data, **kwargs):
        return CustomFeedInfo(**data)


class DynamoDbSiteSchema(Schema):
    host = fields.String()
    last_seen = fields.DateTime()
    PK = fields.Method("site_primary_key")
    SK = fields.Method("site_sort_key")

    def site_primary_key(self, obj):
        if not obj.host:
            raise ValidationError("Host value must exist.")
        return f"SITE#{obj.host}"

    def site_sort_key(self, obj):
        if not obj.host:
            raise ValidationError("Host value must exist.")
        return f"#METADATA#{obj.host}"

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
