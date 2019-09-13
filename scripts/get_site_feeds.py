import boto3
from pprint import pprint
from gateway.schema import DynamoDbFeedInfoSchema, DynamoDbSiteSchema
from boto3.dynamodb.conditions import Key, Attr
from gateway.dynamodb_storage import load_feeds, save_feeds

# dynamodb = boto3.client("dynamodb")

feed_schema = DynamoDbFeedInfoSchema(many=True)
site_schema = DynamoDbSiteSchema()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("feedsearch")


def fetch_site_feeds(site):
    # resp = dynamodb.query(
    #     TableName="feedsearch",
    #     KeyConditionExpression="PK = :pk",
    #     ExpressionAttributeValues={":pk": {"S": f"SITE#{site}"}},
    #     ScanIndexForward=True,
    # )
    resp = table.query(KeyConditionExpression=Key("PK").eq(f"SITE#{site}"))

    pprint(resp)
    site = site_schema.load(resp.get("Items")[0])
    feeds = feed_schema.load(resp.get("Items")[1:])
    pprint(site)
    pprint(feeds)


def fetch_feed():
    resp = table.get_item(Key={"PK": "SITE#test.com", "SK": "#METADATA#test.com"})
    pprint(resp)


# fetch_site_feeds("test.com")
# fetch_feed()

site_info = load_feeds("arstechnica.com")
pprint(site_info)
