from abc import ABC, abstractmethod

from marshmallow import Schema, EXCLUDE

from gateway.schema.external_feedinfo_schema import ExternalFeedInfoSchema


class DynamoDBSchema(ABC):
    @abstractmethod
    def serialize_primary_key(self, obj):
        raise NotImplementedError

    @abstractmethod
    def serialize_sort_key(self, obj):
        raise NotImplementedError

    @property
    @abstractmethod
    def primary_key_prefix(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def sort_key_prefix(self):
        raise NotImplementedError

    @classmethod
    def create_primary_key(cls, value: str) -> str:
        return f"{cls.primary_key_prefix}{value}"

    @classmethod
    def create_sort_key(cls, value: str) -> str:
        return f"{cls.sort_key_prefix}{value}"

    class Meta:
        # Pass EXCLUDE as Meta option to keep marshmallow 2 behavior
        unknown = EXCLUDE


class ExternalFeedInfoSchemaDynamoDbMeta(
    type(ExternalFeedInfoSchema), type(DynamoDBSchema)
):
    pass


class SchemaDynamoDbMeta(type(Schema), type(DynamoDBSchema)):
    pass
