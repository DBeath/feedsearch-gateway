from datetime import datetime

from feedsearch_crawler import FeedInfo
from marshmallow import (
    Schema,
    fields,
    post_load,
    EXCLUDE,
    ValidationError,
    pre_load,
    post_dump,
)


class NoneString(fields.String):
    def _serialize(self, value, attr, obj, **kwargs):
        if value == "":
            return None
        return super(NoneString, self)._serialize(value, attr, obj, **kwargs)


class FeedInfoSchema(Schema):
    url = fields.Url()
    site_url = NoneString(allow_none=True)
    title = NoneString(allow_none=True)
    description = NoneString(allow_none=True)
    site_name = NoneString(allow_none=True)
    favicon = NoneString(allow_none=True)
    hubs = fields.List(NoneString(), allow_none=True)
    is_push = fields.Boolean(allow_none=True, default=False)
    content_type = NoneString(allow_none=True)
    content_length = fields.Integer(allow_none=True, strict=False, default=0)
    bozo = fields.Integer(allow_none=True, strict=False, default=0)
    version = NoneString(allow_none=True)
    self_url = NoneString(allow_none=True)
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
