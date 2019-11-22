from marshmallow import fields, ValidationError
from yarl import URL


class NoneString(fields.String):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValidationError("value must be a string or None")
        if not value or not value.strip():
            return None
        return super(NoneString, self)._serialize(value, attr, obj, **kwargs)


class URLField(fields.String):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if not isinstance(value, (URL, str)):
            raise ValidationError("value must be a URL, string, or None")
        value = str(value)
        if not value.strip():
            return None
        return super(URLField, self)._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, (str, bytes)):
            raise self.make_error("invalid")
        try:
            return URL(value)
        except Exception as error:
            raise self.make_error("invalid") from error
