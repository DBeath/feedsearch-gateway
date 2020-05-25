import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Union, Set

from dateutil.tz import tzutc
from feedsearch_crawler import FeedsearchSpider, sort_urls
from flask import current_app as app
from werkzeug.exceptions import abort
from yarl import URL

from gateway.dynamodb_storage import (
    db_load_site_feeds,
    db_save_site_feeds,
    db_load_site_path,
)
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


def crawl(urls: List[URL], checkall) -> Tuple[list, dict]:
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


def run_search(
    db_table,
    query_url: URL,
    check_feedly: bool = True,
    force_crawl: bool = False,
    check_all: bool = False,
    skip_crawl: bool = False,
) -> Tuple[List[CustomFeedInfo], Dict]:
    """
    Run a search of the query URL.

    :param db_table: Dynamodb Table
    :param query_url: URL to be searched
    :param check_feedly: Query Feedly for feeds matching the query url
    :param force_crawl: Force a crawl of the query url
    :param skip_crawl: Skip the crawl unless force_crawl is True
    :param check_all: Check additional paths of the query url
    :return: Tuple of List of Feeds and crawl stats
    """
    searching_path: bool = has_path(query_url)
    # Remove certain feed or www. subdomains to get the root host domain. This way it's easier to match feeds
    # that may be on specialised feed subdomains with the host website.
    host: str = remove_subdomains(query_url.host)

    site = SiteHost(host)
    site_path = SitePath(host, query_url.path)
    crawl_stats: Dict = {}

    if app.config.get("DYNAMODB_TABLE"):
        load_start = time.perf_counter()
        site = db_load_site_feeds(db_table, site)
        load_duration = int((time.perf_counter() - load_start) * 1000)
        app.logger.info(
            "Site DB Load: feeds=%d duration=%d", len(site.feeds), load_duration
        )

        # Check if the path has already been crawled recently, and if so return matching feeds.
        if searching_path and site.feeds and not force_crawl:
            load_start = time.perf_counter()
            site_path: SitePath = db_load_site_path(db_table, site_path)
            load_duration = int((time.perf_counter() - load_start) * 1000)
            app.logger.info(
                "Sitepath DB Load: feeds=%d duration=%d",
                len(site_path.feeds),
                load_duration,
            )

            site_path_crawled_recently = seen_recently(
                site_path.last_seen, app.config.get("DAYS_CHECKED_RECENTLY")
            )

            # Return previously found feeds if path has already been crawled recently.
            if site_path_crawled_recently:
                matching_feeds: Set[CustomFeedInfo] = set()
                for url in site_path.feeds:
                    feed = site.feeds.get(url)
                    if feed:
                        matching_feeds.add(feed)

                return list(matching_feeds), crawl_stats

    # Calculate if the site was recently crawled.
    site_crawled_recently = seen_recently(
        site.last_seen, app.config.get("DAYS_CHECKED_RECENTLY")
    )

    crawl_feed_list: List[CustomFeedInfo] = []
    crawled = False

    # Crawl the site if the following conditions are met.
    if should_run_crawl(
        force_crawl=force_crawl,
        skip_crawl=skip_crawl,
        searching_path=searching_path,
        crawled_recently=site_crawled_recently,
    ):
        crawl_start_urls: Set[URL] = {query_url}
        existing_urls: List[str] = list(site.feeds.keys())

        # Fetch feeds from feedly.com
        if check_feedly and not site_crawled_recently:
            feedly_urls = fetch_feedly_feeds(str(query_url))
            if feedly_urls:
                crawl_start_urls.update(
                    validate_feedly_urls(feedly_urls, existing_urls, host)
                )

        # Check each feed again if it has not been crawled recently.
        if not searching_path:
            for feed in site.feeds.values():
                if not seen_recently(
                    feed.last_seen, app.config.get("DAYS_CHECKED_RECENTLY")
                ):
                    crawl_start_urls.add(feed.url)

        # Crawl the start urls.
        crawl_feed_list, crawl_stats = crawl(list(crawl_start_urls), check_all)
        crawled = True

    now = force_utc(datetime.now(tzutc()))
    site.last_seen = now

    for feed in crawl_feed_list:
        CustomFeedInfo.upgrade_feedinfo(feed)
        feed.last_seen = now
        feed.host = site.host
        existing_feed = site.feeds.get(str(feed.url))
        if existing_feed:
            feed.merge(existing_feed)
        if feed.is_valid:
            site.feeds[str(feed.url)] = feed

    all_feeds: List[CustomFeedInfo] = list(site.feeds.values())

    for feed in all_feeds:
        score_item(feed, host)
        feed.host = site.host
        if feed.last_updated:
            feed.last_updated = force_utc(feed.last_updated)

    # Only upload new file if crawl occurred.
    if (
        crawled
        and app.config.get("DYNAMODB_TABLE")
        and crawl_stats
        and 200 in crawl_stats.get("status_codes")
    ):
        site_path.feeds = [str(feed.url) for feed in crawl_feed_list]
        site_path.last_seen = now
        save_start = time.perf_counter()
        db_save_site_feeds(db_table, site, all_feeds, site_path)
        save_duration = int((time.perf_counter() - save_start) * 1000)
        app.logger.info(
            "Site DB Save: feeds=%d duration=%d", len(all_feeds), save_duration
        )

    # If the requested URL has a path component, then only return the feeds found from the crawl.
    if searching_path:
        feed_list = crawl_feed_list
    else:
        feed_list = all_feeds

    return feed_list, crawl_stats
