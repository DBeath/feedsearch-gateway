import asyncio
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Union, Set

from dateutil.tz import tzutc
from feedsearch_crawler import FeedsearchSpider, sort_urls, FeedInfo
from flask import current_app as app
from werkzeug.exceptions import abort
from yarl import URL

from gateway.dynamodb_client import DynamoDBClient
from gateway.feedly import fetch_feedly_feeds, validate_feedly_urls
from gateway.schema.customfeedinfo import CustomFeedInfo, score_item
from gateway.schema.sitehost import SiteHost
from gateway.schema.sitepath import SitePath
from gateway.utils import force_utc, remove_subdomains, remove_scheme, has_path


def seen_recently(last_seen: datetime, days: int = 7) -> bool:
    """Calculate if the site was recently crawled."""
    if last_seen:
        if force_utc(last_seen) > (datetime.now(tzutc()) - timedelta(days=days)):
            return True
    return False


def crawl(urls: List[URL], checkall) -> Tuple[List[FeedInfo], Dict]:
    async def run_crawler():
        spider = FeedsearchSpider(
            try_urls=checkall,
            concurrency=20,
            request_timeout=4,
            total_timeout=10,
            max_retries=0,
            max_depth=5,
            delay=0,
            user_agent=app.config.get("USER_AGENT"),
            start_urls=urls,
            crawl_hosts=True,
        )

        await spider.crawl()
        return spider

    try:
        crawler = asyncio.run(run_crawler())
        feed_list = sort_urls(list(crawler.items))
        stats = crawler.get_stats()
        return feed_list, stats
    except Exception as e:
        app.logger.exception("Search error: %s", e)
        abort(500)


def find_feeds_with_matching_url(
    query_url: Union[URL, str], feeds: Dict[str, CustomFeedInfo]
) -> List[CustomFeedInfo]:
    """
    Find a feed whose URL matches the query URL. Ignores url scheme.

    :param query_url: URL to query, as string or URL object.
    :param feeds: Dict of Feeds to query.
    :return: Matching Feed or None
    """
    matches: List[CustomFeedInfo] = []
    query = remove_scheme(query_url)
    for url, feed in feeds:
        if remove_scheme(url) == query:
            matches.append(feed)
    return matches


def should_run_crawl(
    force_crawl: bool, skip_crawl: bool, searching_path: bool, crawled_recently: bool
) -> bool:
    """
    Check whether to run the crawl.

    Always crawl if force_crawl is True.
    Otherwise, never crawl if skip_crawl is True.

    Assuming neither of the above are true, then crawl if searching_path is True or crawled_recently is False.

    :param force_crawl: Always crawl if True.
    :param skip_crawl: Never crawl if True, unless force_crawl is also True.
    :param searching_path: If the above are both false, then crawl if we're searching a path.
    :param crawled_recently: If all the above are False, then crawl if this is also False, as we
        haven't crawled this path recently.
    :return: True if we should crawl.
    """
    if force_crawl:
        return True
    elif skip_crawl:
        return False
    elif searching_path:
        return True
    elif not crawled_recently:
        return True
    return False


class SearchRunner:
    def __init__(
        self,
        db_client: DynamoDBClient,
        check_feedly: bool = True,
        force_crawl: bool = True,
        check_all: bool = False,
        skip_crawl: bool = True,
        days_checked_recently: int = 7,
    ):
        self.db_client = db_client
        self.check_feedly = check_feedly
        self.force_crawl = force_crawl
        self.check_all = check_all
        self.skip_crawl = skip_crawl
        self.days_checked_recently = days_checked_recently
        self.searching_path: bool = False
        self.host: str = ""
        self.site = None
        self.site_path = None
        self.crawl_stats: Dict = {}
        self.site_crawled_recently: bool = False
        self.feeds: List[CustomFeedInfo] = []
        self.crawl_feed_list: List[CustomFeedInfo] = []
        self.upgraded_crawled_feeds: List[CustomFeedInfo] = []
        self.crawled: bool = False
        self.query_url: URL = URL()

    def run_search(self, query_url: URL) -> List[CustomFeedInfo]:
        """
        Run a search crawl of the query URL for Feeds, querying the database for existing Feeds, and saving the results
        of the crawl back to the database.

        :param query_url: Initial URL start the crawl
        :return: List of found Feeds
        """
        self.query_url = query_url
        self.searching_path = has_path(query_url)
        # Remove certain feed or www. subdomains to get the root host domain. This way it's easier to match feeds
        # that may be on specialised feed subdomains with the host website.
        self.host: str = remove_subdomains(query_url.host)

        self.site = SiteHost(self.host)
        self.site_path = SitePath(self.host, query_url.path)
        self.crawl_stats: Dict = {}

        # Query existing data for the site
        existing_site = self.db_client.query_site_feeds(self.site)
        if existing_site:
            self.site = existing_site

        # Query the site path info from DynamoDB
        if self.should_query_site_path(
            self.searching_path, bool(self.site.feeds), self.force_crawl
        ):
            self.check_site_path()

        # Return previously found feeds if path has already been crawled recently.
        if seen_recently(self.site_path.last_seen, self.days_checked_recently):
            return self.match_existing_feeds_to_path(
                self.site_path.feeds, self.site.feeds
            )

        # Calculate if the site was recently crawled.
        self.site_crawled_recently = seen_recently(
            self.site.last_seen, self.days_checked_recently
        )

        # Crawl the site if the following conditions are met.
        if should_run_crawl(
            force_crawl=self.force_crawl,
            skip_crawl=self.skip_crawl,
            searching_path=self.searching_path,
            crawled_recently=self.site_crawled_recently,
        ):
            crawl_start_urls: List[URL] = [query_url]

            # Check Feedly for feed urls
            if self.should_check_feedly(self.check_feedly, self.site_crawled_recently):
                feedly_urls = self.run_feedly_check(query_url)
                crawl_start_urls.extend(feedly_urls)

            # Check each feed again if it has not been crawled recently.
            if not self.searching_path:
                crawl_start_urls.extend(
                    self.filter_feeds_to_crawl(
                        list(self.site.feeds.values()), self.days_checked_recently
                    )
                )

            # Crawl the start urls.
            self.crawl_feed_list, self.crawl_stats = crawl(
                list(crawl_start_urls), self.check_all
            )
            self.crawled = True

        now: datetime = force_utc(datetime.now(tzutc()))
        self.site.last_seen = now

        # Update the crawled feeds with site info
        self.upgraded_crawled_feeds = self.update_crawled_feeds(
            self.crawl_feed_list, self.site, now
        )

        all_feeds: List[CustomFeedInfo] = list(self.site.feeds.values())

        # Score the feeds
        self.score_feeds(all_feeds, self.site.host)

        # Only upload new file if crawl occurred.
        if (
            self.crawled
            and self.crawl_stats
            and 200 in self.crawl_stats.get("status_codes")
        ):
            self.site_path.feeds = [
                str(feed.url) for feed in self.upgraded_crawled_feeds
            ]
            self.site_path.last_seen = now
            self.db_client.save_site_feeds(self.site, all_feeds, self.site_path)

        # If the requested URL has a path component, then only return the feeds found from the crawl.
        if self.searching_path:
            return self.upgraded_crawled_feeds
        else:
            return all_feeds

    @staticmethod
    def score_feeds(feeds: List[CustomFeedInfo], host: str) -> None:
        """
        Score feeds according to the queried URL

        :param feeds: List of feeds to score
        :param host: Root domain of queried URL
        """
        for feed in feeds:
            score_item(feed, host)
            feed.host = host
            if feed.last_updated:
                feed.last_updated = force_utc(feed.last_updated)

    @staticmethod
    def update_crawled_feeds(
        crawled_feeds: List[FeedInfo], site: SiteHost, now: datetime
    ) -> List[CustomFeedInfo]:
        """
        Update the crawled feeds from FeedInfo to CustomFeedInfo, and add site info.
        Return only valid feeds.

        :param crawled_feeds: List of crawled FeedInfo objects
        :param site: SiteHost
        :param now: current datetime
        :return: Upgraded CustomFeedInfo objects
        """
        upgraded_crawled_feeds: List[CustomFeedInfo] = []
        for feed in crawled_feeds:
            CustomFeedInfo.upgrade_feedinfo(feed)
            feed: CustomFeedInfo
            feed.last_seen = now
            feed.host = site.host

            if existing_feed := site.feeds.get(str(feed.url)):
                feed.merge(existing_feed)

            if feed.is_valid:
                site.feeds[str(feed.url)] = feed
                upgraded_crawled_feeds.append(feed)

        return upgraded_crawled_feeds

    @staticmethod
    def filter_feeds_to_crawl(
        feeds: List[CustomFeedInfo], days_checked_recently: int
    ) -> List[URL]:
        """
        Filter existing feeds to crawl according to how recently they've been crawled.

        :param feeds: List of existing feeds
        :param days_checked_recently: How recently a feed is allowed to have been crawled in days
        :return: Feeds to add to initial crawl list
        """
        crawl_feeds: List[URL] = []
        for feed in feeds:
            if not seen_recently(feed.last_seen, days_checked_recently):
                crawl_feeds.append(feed.url)
        return crawl_feeds

    @staticmethod
    def should_query_site_path(
        searching_path: bool, has_site_feeds: bool, force_crawl: bool
    ) -> bool:
        """
        Check if existing site path information should be queried.

        :param searching_path: Current search path
        :param has_site_feeds: Whether the current site has existing found feeds
        :param force_crawl: If the crawl should be forced regardless
        :return: True if the path should be queried
        """
        return searching_path and has_site_feeds and not force_crawl

    def check_site_path(self) -> None:
        """
        Query the database for existing site path information
        """
        existing_site_path = self.db_client.query_site_path(self.site_path)
        if existing_site_path:
            self.site_path = existing_site_path

    @staticmethod
    def should_check_feedly(check_feedly: bool, site_crawled_recently: bool) -> bool:
        """
        Check if Feedly should be queried for feed urls

        :param check_feedly: Whether Feedly should be queried
        :param site_crawled_recently: Whether the site has already been crawled recently
        :return: True if Feedly should be queried
        """
        return check_feedly and not site_crawled_recently

    def run_feedly_check(self, query_url: URL) -> List[URL]:
        """
        Fetch list of feed URLs from feedly.com for the given query URL

        :return: List of URLs
        """
        existing_urls: List[str] = list(self.site.feeds.keys())
        feedly_urls = fetch_feedly_feeds(str(query_url))
        if not feedly_urls:
            return []

        validated_feedly_urls = validate_feedly_urls(
            existing_urls=existing_urls, feedly_urls=feedly_urls, host=self.host
        )
        return validated_feedly_urls

    @staticmethod
    def match_existing_feeds_to_path(
        site_path_feeds: List[str], site_feeds: Dict[str, CustomFeedInfo]
    ) -> List[CustomFeedInfo]:
        """
        Matches previously found feeds at this site to the current site path

        :param site_path_feeds: List of feeds previously found at this query path
        :param site_feeds: List of all feeds found at this site
        :return: Matched feeds
        """
        matching_feeds: Set[CustomFeedInfo] = set()
        for url in site_path_feeds:
            feed = site_feeds.get(url)
            if feed:
                matching_feeds.add(feed)

        return list(matching_feeds)
