from marshmallow import Schema, fields, EXCLUDE

from gateway.schema.external_feedinfo_schema import ExternalFeedInfoSchema


class ExternalSiteSchema(Schema):
    host = fields.String()
    last_seen = fields.DateTime()
    feeds = fields.Nested(ExternalFeedInfoSchema, many=True)

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE
