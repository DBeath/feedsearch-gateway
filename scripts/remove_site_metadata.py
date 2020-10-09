import logging
from typing import List, Dict
import time

import boto3
import click
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from marshmallow import ValidationError

from gateway.schema.dynamodb_site_schema import DynamoDbSiteSchema
from gateway.schema.sitehost import SiteHost

dynamodb = boto3.resource("dynamodb")

logger = logging.getLogger(__name__)

db_site_schema = DynamoDbSiteSchema()
db_site_schema_many = DynamoDbSiteSchema(many=True)


def load_sites(items: List[Dict]) -> List[SiteHost]:
    sites: List[SiteHost] = []

    for item in items:
        try:
            site: SiteHost = db_site_schema.load(item)
            sites.append(site)
        except ValidationError as e:
            logger.exception("Dump errors: %s", e.messages)
            raise click.Abort()

    return sites


def write_sites(table, sites: List[SiteHost], items: List[Dict]) -> None:
    click.echo("Rewriting sites %s" % [site.host for site in sites])

    try:
        dumped_sites: Dict = db_site_schema_many.dump(sites)
    except ValidationError as e:
        logger.exception("Dump errors: %s", e.messages)
        raise click.Abort()

    try:
        with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
            for item in items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
            for item in dumped_sites:
                batch.put_item(Item=item)
    except (ClientError, ValidationError) as e:
        logger.error(e)
        raise click.Abort()


def process_response(table, response):
    scanned = 0
    rewritten_count = 0

    if "Items" not in response:
        click.echo("No items in response")
        click.Abort()

    if "ScannedCount" in response:
        scanned += response["ScannedCount"]

    sites = load_sites(response["Items"])
    write_sites(table, sites, response["Items"])
    rewritten_count += len(sites)
    return scanned, rewritten_count


@click.command()
@click.option("--table_name", prompt="DynamoDB Table Name", help="DynamoDB Table Name")
def rewrite_metadata(table_name) -> None:
    """
    Rewrites site metadata by deleting and then putting site.
    """
    table = dynamodb.Table(table_name)

    if not click.confirm(
        f"Are you sure you want to rewrite site metadata in table {table_name}?"
    ):
        return

    rewritten_count = 0

    queries = 0
    scanned = 0
    start = time.perf_counter()

    try:
        response = table.scan(
            FilterExpression=Key("SK").begins_with(DynamoDbSiteSchema.sort_key_prefix)
        )
        queries += 1

        q_scanned, q_rewritten = process_response(table, response)
        scanned += q_scanned
        rewritten_count += q_rewritten

        current_time = time.perf_counter()
        duration_ms = int((current_time - start) * 1000)
        click.echo(
            f"Query: {queries}, Rewritten: {rewritten_count}, Scanned: {scanned}, Duration: {duration_ms}ms"
        )

        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Key("SK").begins_with(
                    DynamoDbSiteSchema.sort_key_prefix
                ),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            queries += 1

            q_scanned, q_rewritten = process_response(table, response)
            scanned += q_scanned
            rewritten_count += q_rewritten

            current_time = time.perf_counter()
            duration_ms = int((current_time - start) * 1000)
            click.echo(
                f"Query: {queries}, Rewritten: {rewritten_count}, Scanned: {scanned}, Duration: {duration_ms}ms"
            )

    except ClientError as e:
        logger.exception(e)
        raise click.Abort()
    finally:
        end = time.perf_counter()
        duration_ms = int((end - start) * 1000)
        click.echo(
            f"Finished rewriting sites. Rewritten: {rewritten_count}, Queries: {queries}, Scanned: {scanned}, "
            f"Duration: {duration_ms}ms, Table: {table_name}"
        )


if __name__ == "__main__":
    rewrite_metadata()
