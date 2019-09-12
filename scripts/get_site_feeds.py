import boto3

dynamodb = boto3.client("dynamodb")


def fetch_site_feeds(site):
    resp = dynamodb.query(
        TableName="feedsearch",
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": {"S": f"SITE#{site}"}},
        ScanIndexForward=True,
    )
    print(resp)


fetch_site_feeds("test.com")
