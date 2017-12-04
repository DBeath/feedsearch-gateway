from feedsearch.feedinfo import FeedInfo
from marshmallow import Schema, fields, post_load

class FeedInfoSchema(Schema):
    url = fields.Url()
    site_url = fields.String(allow_none=True)
    title = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    site_name = fields.String(allow_none=True)
    favicon = fields.String(allow_none=True)
    hub = fields.String(allow_none=True)
    is_push = fields.Boolean(allow_none=True)
    content_type = fields.String(allow_none=True)
    bozo = fields.Integer(allow_none=True)
    version = fields.String(allow_none=True)
    self_url = fields.String(allow_none=True)
    score = fields.Integer(allow_none=True)
    favicon_data_uri = fields.String(allow_none=True)

    @post_load
    def make_feed_info(self, data):
        return FeedInfo(**data)

FEED_INFO_SCHEMA = FeedInfoSchema(many=True)
