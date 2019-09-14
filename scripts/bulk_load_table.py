import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")

table_name = os.environ["DYNAMODB_TABLE"]
table = dynamodb.Table(table_name)

items = []

with open("scripts/items.json", "r") as f:
    for row in f:
        items.append(json.loads(row))

with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)
