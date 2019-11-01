import logging
import time
from datetime import datetime
from typing import Dict, List

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from marshmallow import ValidationError

from gateway.schema import (
    DynamoDbFeedInfoSchema,
    DynamoDbSiteSchema,
    DynamoDbSitePathSchema,
)

db_feed_schema = DynamoDbFeedInfoSchema(many=True)
db_site_schema = DynamoDbSiteSchema()
db_path_schema = DynamoDbSitePathSchema()

logger = logging.getLogger("dynamodb")


def db_load_site_feeds(table, host: str) -> Dict:
    try:
        query_start = time.perf_counter()
        key = f"SITE#{host}"
        resp = table.query(KeyConditionExpression=Key("PK").eq(key))
        duration = int((time.perf_counter() - query_start) * 1000)
        logger.debug("Site Query: key=%s duration=%d", key, duration)
    except ClientError as e:
        logger.error(e)
        return {}

    if not resp.get("Items"):
        return {}

    try:
        load_start = time.perf_counter()
        site = db_site_schema.load(resp.get("Items")[0])
        feeds = db_feed_schema.load(resp.get("Items")[1:])
        site["feeds"] = feeds
        duration = int((time.perf_counter() - load_start) * 1000)
        logger.debug("Site Load: key=%s duration=%d", key, duration)
        return site
    except ValidationError as e:
        logger.warning("Dump errors: %s", e.messages)
    except IndexError as e:
        logger.error(e)


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


def db_save_site_feeds(table, host: str, last_seen: datetime, feeds) -> None:
    try:
        site = {"host": host, "last_seen": last_seen}
        for feed in feeds:
            feed.host = host
        dumped_site = db_site_schema.dump(site)
        dumped_feeds = db_feed_schema.dump(feeds)
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
