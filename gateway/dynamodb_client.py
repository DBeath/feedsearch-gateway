import logging

import boto3
import time
from typing import Dict, List, Union

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from marshmallow import ValidationError

from gateway.schema.customfeedinfo import CustomFeedInfo
from gateway.schema.dynamodb_feedinfo_schema import DynamoDbFeedInfoSchema
from gateway.schema.dynamodb_site_schema import DynamoDbSiteSchema
from gateway.schema.dynamodb_sitepath_schema import DynamoDbSitePathSchema
from gateway.schema.sitehost import SiteHost
from gateway.schema.sitepath import SitePath

from sentry_sdk import capture_exception


logger = logging.getLogger(__name__)


class DynamoDBClient:
    db_feed_schema = DynamoDbFeedInfoSchema(many=True)
    db_site_schema = DynamoDbSiteSchema()
    db_path_schema = DynamoDbSitePathSchema()

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def _paginate_query(self, query_name, **kwargs) -> List[Dict]:
        """
        Paginate a DynamoDB query and return the found Items.

        :param **kwargs: Boto3 query arguments
        :return: List of Items from query results
        """
        items = []
        queries = 0
        query_start = time.perf_counter()

        try:
            response = self.table.query(**kwargs)
            queries += 1

            if "Items" not in response:
                return items

            items.extend(response["Items"])

            while "LastEvaluatedKey" in response:
                kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.query(**kwargs)
                queries += 1

                if "Items" not in response:
                    return items

                items.extend(response["Items"])

        except ClientError as e:
            capture_exception(e)
            logger.error(e)
            return []
        finally:
            duration = int((time.perf_counter() - query_start) * 1000)

            logger.debug(
                "DB_QUERY: query=%s duration=%d queries=%d",
                query_name,
                duration,
                queries,
            )

        return items

    def load_site_feeds(self, items: List[Dict]) -> SiteHost:
        """
        Load items from DynamoDB into SiteHost and Feeds.

        :param items: List of DynamoDB items
        :return: SiteHost object
        """
        try:
            site: SiteHost = self.db_site_schema.load(items[0])
            feeds: List[CustomFeedInfo] = self.db_feed_schema.load(items[1:])
            site.load_feeds(feeds)
            return site
        except ValidationError as e:
            capture_exception(e)
            logger.warning("Dump errors: %s", e.messages)
        except IndexError as e:
            capture_exception(e)
            logger.error(e)

    def query_site_feeds(self, site: Union[str, SiteHost]) -> SiteHost:
        """
        Queries DynamoDB for the SiteHost and all its associated Feeds.

        :param site: SiteHost object or string of website domain root
        :return: SiteHost object containing associated Feeds
        """
        if isinstance(site, str):
            site = SiteHost(site)
        try:
            key = DynamoDbSiteSchema.create_primary_key(site.host)
            items = self._paginate_query(
                "SiteHost",
                KeyConditionExpression=Key("PK").eq(key)
                & Key("SK").between("#METADATA#", "FEED$"),
            )
        except ClientError as e:
            capture_exception(e)
            logger.error(e)
            return site

        if not items:
            return site

        if loaded_site := self.load_site_feeds(items):
            return loaded_site
        else:
            return site

    def load_site_path(self, items: List[Dict]) -> SitePath:
        """
        Load items from DynamoDB into SitePath object.

        :param items: List of DynamoDB items
        :return: SitePath object
        """
        try:
            existing_path = self.db_path_schema.load(items[0])
            return existing_path
        except ValidationError as e:
            capture_exception(e)
            logger.error("Dump errors: %s", e.messages)
        except IndexError as e:
            capture_exception(e)
            logger.error(e)

    def query_site_path(self, site_path: SitePath) -> SitePath:
        """
        Queries DynamoDB for the given SitePath.

        :param site_path: SitePath record to query
        :return: SitePath record
        """
        try:
            key = DynamoDbSitePathSchema.create_primary_key(site_path.host)
            sort_key = DynamoDbSitePathSchema.create_sort_key(site_path.path)
            items = self._paginate_query(
                "SitePath",
                KeyConditionExpression=Key("PK").eq(key) & Key("SK").eq(sort_key),
            )
        except ClientError as e:
            capture_exception(e)
            logger.error(e)
            return site_path

        if not items:
            return site_path

        if loaded_path := self.load_site_path(items):
            return loaded_path

        return site_path

    def save_site_feeds(
        self, site: SiteHost, feeds: List[CustomFeedInfo], site_path: SitePath
    ) -> None:
        """
        Saves the SiteHost, its list of Feeds, and the queried SitePath to DynamoDB.

        :param site: SiteHost object
        :param feeds: List of CustomFeedInfo
        :param site_path: SitePath object
        """
        try:
            dumped_site: Dict = self.db_site_schema.dump(site)
            dumped_feeds: Dict = self.db_feed_schema.dump(feeds)
            dumped_site_path: Dict = self.db_path_schema.dump(site_path)
        except ValidationError as e:
            logger.error("Dump errors: %s", e.messages)
            return

        try:
            with self.table.batch_writer() as batch:
                batch.put_item(dumped_site)
                batch.put_item(dumped_site_path)
                for item in dumped_feeds:
                    batch.put_item(Item=item)
        except (ClientError, ValidationError) as e:
            capture_exception(e)
            logger.error(e)

    @staticmethod
    def load_sites_list(items: List[Dict]) -> List[Dict]:
        """
        Load items from DynamoDB into a list of sites.

        :param items: List of DynamoDB items
        :return: List of sites as Dict
        """
        sites: List[Dict] = []

        for item in items:
            try:
                site = {
                    "host": item.get("host"),
                    "last_seen": item.get("last_seen"),
                }
                sites.append(site)
            except KeyError as e:
                capture_exception(e)
                logger.error("Missing required value: %s", e)
        return sites

    def query_sites_list(self) -> List[Dict]:
        """
        Query DynamoDB for all Sites.

        :return: List of SiteHosts
        """
        items = self._paginate_query(
            "All_Sites",
            IndexName="InvertedIndex",
            KeyConditionExpression=Key("SK").eq(DynamoDbSiteSchema.sort_key_prefix),
        )

        return self.load_sites_list(items)
