import logging
from typing import List, Dict

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


def load_sites(this_response) -> List[SiteHost]:
    sites: List[SiteHost] = []

    for item in this_response["Items"]:
        try:
            site: SiteHost = db_site_schema.load(item)
            sites.append(site)
        except ValidationError as e:
            logger.exception("Dump errors: %s", e.messages)
            raise click.Abort()

    return sites


def write_sites(table, sites: List[SiteHost]) -> None:
    click.echo("Rewriting sites %s" % [site.host for site in sites])

    try:
        dumped_sites: Dict = db_site_schema_many.dump(sites)
    except ValidationError as e:
        logger.exception("Dump errors: %s", e.messages)
        raise click.Abort()

    try:
        with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
            for item in sites:
                click.echo(item)
                batch.delete_item(
                    Key={
                        "PK": DynamoDbSiteSchema.create_primary_key(item.host),
                        "SK": DynamoDbSiteSchema.create_sort_key(item.host),
                    }
                )

        with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
            for item in dumped_sites:
                batch.put_item(Item=item)
    except (ClientError, ValidationError) as e:
        logger.error(e)
        raise click.Abort()


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

    try:
        response = table.scan(
            FilterExpression=Key("SK").begins_with(DynamoDbSiteSchema.sort_key_prefix)
        )

        if "Items" not in response:
            return

        sites = load_sites(response)
        write_sites(table, sites)
        rewritten_count += len(sites)

        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=Key("SK").begins_with(
                    DynamoDbSiteSchema.sort_key_prefix
                ),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )

            if "Items" not in response:
                return

            sites = load_sites(response)
            write_sites(table, sites)
            rewritten_count += len(sites)

    except ClientError as e:
        logger.exception(e)
        raise click.Abort()
    finally:
        click.echo("Rewrote %d sites" % rewritten_count)


if __name__ == "__main__":
    rewrite_metadata()
