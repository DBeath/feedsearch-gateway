import asyncio
from datetime import datetime, timedelta
from typing import List, Tuple

from dateutil.tz import tzutc
from feedsearch_crawler import FeedsearchSpider, sort_urls
from flask import current_app as app
from werkzeug.exceptions import abort
from yarl import URL

from gateway.utils import force_utc


def site_checked_recently(last_checked: datetime, days: int = 7) -> bool:
    """Calculate if the site was recently crawled."""
    if last_checked:
        if force_utc(last_checked) > (datetime.now(tzutc()) - timedelta(days=days)):
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
