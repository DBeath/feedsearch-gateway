import click
import boto3
from boto3.dynamodb.conditions import Key
import time

from gateway.schema.dynamodb_site_schema import DynamoDbSiteSchema

dynamodb = boto3.resource("dynamodb")


@click.command()
@click.option("--table_name", prompt="DynamoDB Table Name", help="DynamoDB Table Name")
def count_sites(table_name) -> None:
    table = dynamodb.Table(table_name)
    count = 0
    queries = 0
    scanned = 0
    start = time.perf_counter()

    response = table.scan(
        FilterExpression=Key("SK").begins_with(DynamoDbSiteSchema.sort_key_prefix),
        Select="COUNT",
    )
    queries += 1
    if "Count" in response:
        count += response["Count"]
    if "ScannedCount" in response:
        scanned += response["ScannedCount"]

    click.echo(f"Query: {queries}, Count: {count}, Scanned: {scanned}")

    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=Key("SK").begins_with(DynamoDbSiteSchema.sort_key_prefix),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        queries += 1
        if "Count" in response:
            count += response["Count"]
        if "ScannedCount" in response:
            scanned += response["ScannedCount"]

        click.echo(f"Query: {queries}, Count: {count}, Scanned: {scanned}")

    end = time.perf_counter()
    duration_ms = int((end - start) * 1000)
    click.echo(
        f"Finished counting sites. Site count: {count}, Queries: {queries}, Scanned: {scanned}, "
        f"Duration: {duration_ms}ms, Table: {table_name}"
    )


if __name__ == "__main__":
    count_sites()
