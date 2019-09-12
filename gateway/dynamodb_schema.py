from feedsearch_crawler import FeedInfo
from marshmallow import Schema, fields, post_load, EXCLUDE
from gateway.schema import CustomFeedInfo


class FeedDbSchema(Schema):
    PK = fields.String(required=True)
