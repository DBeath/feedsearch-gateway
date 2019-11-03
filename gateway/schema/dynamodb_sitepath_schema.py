from marshmallow import Schema, fields, ValidationError, post_load, EXCLUDE

from gateway.schema.sitepath import SitePath
from gateway.schema.dynamodb_schema_base import DynamoDBSchema, SchemaDynamoDbMeta
from gateway.schema.fields import NoneString


class DynamoDbSitePathSchema(Schema, DynamoDBSchema, metaclass=SchemaDynamoDbMeta):
    primary_key_prefix = "SITEPATH#"
    sort_key_prefix = "PATH#"

    host = fields.Method(
        "serialize_primary_key", deserialize="load_host", data_key="PK"
    )
    path = fields.Method("serialize_sort_key", deserialize="load_path", data_key="SK")
    last_seen = fields.DateTime()
    feeds = fields.List(NoneString(), allow_none=True)

    def serialize_primary_key(self, obj):
        if not obj.host:
            raise ValidationError("Host value must exist.")
        return self.create_primary_key(obj.host)

    def serialize_sort_key(self, obj):
        if not obj.path:
            raise ValidationError("Path value must exist.")
        return self.create_sort_key(obj.path)

    def load_host(self, value):
        return value.lstrip(self.primary_key_prefix)

    def load_path(self, value):
        return value.lstrip(self.sort_key_prefix)

    # noinspection PyUnusedLocal
    @post_load
    def make_site_path(self, data, **kwargs):
        return SitePath(**data)

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE
