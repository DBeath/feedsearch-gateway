from gateway.schema import DynamoDbFeedInfoSchema, DynamoDbSiteSchema
from boto3.dynamodb.conditions import Key, Attr
import boto3
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("feedsearch")

feed_schema = DynamoDbFeedInfoSchema(many=True)
site_schema = DynamoDbSiteSchema()


def load_feeds(host: str):
    resp = table.query(KeyConditionExpression=Key("PK").eq(f"SITE#{host}"))
    site = site_schema.load(resp.get("Items")[0])
    feeds = feed_schema.load(resp.get("Items")[1:])
    site["feeds"] = feeds
    return site


def save_feeds(host: str, last_seen: datetime, feeds) -> None:
    site = {"host": host, "last_seen": last_seen}
    dumped_site = site_schema.dump(site)
    dumped_feeds = feed_schema.dump(feeds)

    with table.batch_writer() as batch:
        batch.put_item(dumped_site)
        for item in dumped_feeds:
            batch.put_item(Item=item)
