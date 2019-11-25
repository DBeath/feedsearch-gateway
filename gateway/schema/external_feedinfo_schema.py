from marshmallow import Schema, fields, EXCLUDE, post_load

from gateway.schema.customfeedinfo import CustomFeedInfo
from gateway.schema.fields import NoneString, URLField


class ExternalFeedInfoSchema(Schema):
    url = URLField()
    site_url = URLField(allow_none=True)
    title = NoneString(allow_none=True)
    description = NoneString(allow_none=True)
    site_name = NoneString(allow_none=True)
    favicon = URLField(allow_none=True)
    hubs = fields.List(NoneString(), allow_none=True)
    is_podcast = fields.Boolean(allow_none=True, default=False)
    is_push = fields.Boolean(allow_none=True, default=False)
    item_count = fields.Integer(allow_none=True, strict=False, default=0)
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
