from typing import Dict

from feedsearch_crawler import FeedInfo
from marshmallow import Schema, fields, post_load, EXCLUDE, ValidationError
from flask import current_app as app


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
    last_seen = fields.DateTime(allow_none=True, format="%Y-%m-%dT%H:%M:%S+00:00")

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE

    @post_load
    def make_feed_info(self, data, **kwargs):
        return CustomFeedInfo(**data)


class SiteFeedSchema(Schema):
    host = fields.String()
    last_checked = fields.DateTime()
    feeds = fields.Nested(FeedInfoSchema, many=True)

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE


class CustomFeedInfo(FeedInfo):
    last_seen = None

    @property
    def is_valid(self) -> bool:
        return bool(self.url)
