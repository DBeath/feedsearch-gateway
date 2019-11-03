from marshmallow import fields, ValidationError, post_load, post_dump, EXCLUDE

from gateway.schema.customfeedinfo import CustomFeedInfo
from gateway.schema.dynamodb_schema_base import (
    DynamoDBSchema,
    ExternalFeedInfoSchemaDynamoDbMeta,
)
from gateway.schema.external_feedinfo_schema import ExternalFeedInfoSchema


class DynamoDbFeedInfoSchema(
    ExternalFeedInfoSchema, DynamoDBSchema, metaclass=ExternalFeedInfoSchemaDynamoDbMeta
):
    primary_key_prefix = "SITE#"
    sort_key_prefix = "FEED#"

    PK = fields.Method("serialize_primary_key")
    SK = fields.Method("serialize_sort_key")
    host = fields.String()
    velocity = fields.Decimal(allow_none=True)

    def serialize_primary_key(self, obj):
        if not obj.host:
            raise ValidationError("Site Host must exist.")
        return self.create_primary_key(obj.host)

    def serialize_sort_key(self, obj):
        if not obj.url:
            raise ValidationError("URL must exist.")
        return self.create_sort_key(obj.url)

    @post_load
    def make_feed_info(self, data, **kwargs):
        return CustomFeedInfo(**data)

    # noinspection PyUnusedLocal
    @post_dump
    def remove_skip_values(self, data, **kwargs):
        return {key: value for key, value in data.items() if value is not None}

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE
