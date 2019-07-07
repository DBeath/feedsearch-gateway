from marshmallow import Schema, fields, post_load

from .feedinfo import CustomFeedInfo


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

    @post_load
    def make_feed_info(self, data):
        return CustomFeedInfo(**data)


class SiteFeedSchema(Schema):
    host = fields.String()
    last_checked = fields.DateTime()
    feeds = fields.Nested(FeedInfoSchema, many=True)
