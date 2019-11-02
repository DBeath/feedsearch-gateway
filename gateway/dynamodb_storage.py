import logging
import time
from typing import Dict, List, Union

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from marshmallow import ValidationError

from gateway.schema import (
    DynamoDbFeedInfoSchema,
    DynamoDbSiteSchema,
    DynamoDbSitePathSchema,
    SiteHost,
    CustomFeedInfo,
)

db_feed_schema = DynamoDbFeedInfoSchema(many=True)
db_site_schema = DynamoDbSiteSchema()
db_path_schema = DynamoDbSitePathSchema()

logger = logging.getLogger("dynamodb")


def db_load_site_feeds(table, site: Union[str, SiteHost]) -> SiteHost:
    if isinstance(site, str):
        site = SiteHost(site)
    try:
        query_start = time.perf_counter()
        key = DynamoDbSiteSchema.create_primary_key(site.host)
        resp = table.query(KeyConditionExpression=Key("PK").eq(key))
        duration = int((time.perf_counter() - query_start) * 1000)
        logger.debug("Site Query: key=%s duration=%d", key, duration)
    except ClientError as e:
        logger.error(e)
        return site

    if not resp.get("Items"):
        return site

    try:
        load_start = time.perf_counter()
        site: SiteHost = db_site_schema.load(resp.get("Items")[0])
        feeds: List[CustomFeedInfo] = db_feed_schema.load(resp.get("Items")[1:])
        site.feeds = feeds
        duration = int((time.perf_counter() - load_start) * 1000)
        logger.debug("Site Load: key=%s duration=%d", key, duration)
    except ValidationError as e:
        logger.warning("Dump errors: %s", e.messages)
    except IndexError as e:
        logger.error(e)

    return site


def db_load_site_path(table, host: str, path: str) -> Dict:
    try:
        key = f"SITEPATH#{host}"
        sort_key = f"PATH#{path}"
        resp = table.query(
            KeyConditionExpression=Key("PK").eq(key) & Key("SK").eq(sort_key)
        )
    except ClientError as e:
        logger.error(e)
        return {}

    if not resp.get("Items"):
        return {}

    try:
        existing_path = db_path_schema.load(resp.get("Items")[0])
        return existing_path
    except ValidationError as e:
        logger.warning("Dump errors: %s", e.messages)
    except IndexError as e:
        logger.error(e)


def db_save_site_feeds(table, site: SiteHost, feeds: List[CustomFeedInfo]) -> None:
    try:
        for feed in feeds:
            feed.host = site.host
        dumped_site: Dict = db_site_schema.dump(site)
        dumped_feeds: Dict = db_feed_schema.dump(feeds)
    except ValidationError as e:
        logger.warning("Dump errors: %s", e.messages)
        return

    try:
        with table.batch_writer() as batch:
            batch.put_item(dumped_site)
            for item in dumped_feeds:
                batch.put_item(Item=item)
    except ClientError as e:
        logger.error(e)


def db_list_sites(table) -> List[Dict]:
    try:
        resp = table.scan(FilterExpression=Key("SK").begins_with("#METADATA#"))
    except ClientError as e:
        logger.error(e)
        return []

    if not resp.items:
        return []

    sites = []
    for item in resp.get("Items"):
        try:
            site = {"host": item.get("host"), "last_seen": item.get("last_seen")}
            sites.append(site)
        except KeyError as e:
            logger.error("Missing required value: %s", e)

    return sites
