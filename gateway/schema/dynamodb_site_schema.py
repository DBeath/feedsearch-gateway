from marshmallow import Schema, fields, ValidationError, post_load, EXCLUDE

from gateway.schema.sitehost import SiteHost
from gateway.schema.dynamodb_schema_base import DynamoDBSchema, SchemaDynamoDbMeta


class DynamoDbSiteSchema(Schema, DynamoDBSchema, metaclass=SchemaDynamoDbMeta):
    primary_key_prefix = "SITE#"
    sort_key_prefix = "#METADATA#"

    host = fields.String()
    last_seen = fields.DateTime()
    PK = fields.Method("serialize_primary_key")
    SK = fields.Method("serialize_sort_key")

    def serialize_primary_key(self, obj):
        if not obj.host:
            raise ValidationError("Host value must exist.")
        return DynamoDbSiteSchema.create_primary_key(obj.host)

    def serialize_sort_key(self, obj):
        return self.create_sort_key("")

    # noinspection PyUnusedLocal
    @post_load
    def make_site_host(self, data, **kwargs):
        return SiteHost(**data)

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE
