from marshmallow import Schema, fields, EXCLUDE

from gateway.schema.external_feedinfo_schema import ExternalFeedInfoSchema


class ExternalSiteSchema(Schema):
    host = fields.String()
    last_seen = fields.DateTime()
    feeds = fields.Mapping(keys=fields.String(), values=fields.Nested(ExternalFeedInfoSchema))

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE
