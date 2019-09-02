import asyncio
from datetime import datetime, timedelta
from typing import List

import aiohttp
from flask import current_app as app
from yarl import URL

from gateway.utils import truncate_integer


def is_stale_feed(last_updated: int, stale_feed_date: datetime) -> bool:
    """
    Check if the feed's last updated date is older than the stale feed date.

    :param last_updated: Unix timestamp of the date the feed was last updated.
    :param stale_feed_date: Feed should be updated more recently than this date.
    :return: True if the feed is stale.
    """
    if last_updated:
        try:
            # Timestamp from feedly is 13 chars long, so truncate the integer
            last_updated_datetime = datetime.utcfromtimestamp(
                truncate_integer(last_updated)
            )
            # Datetimes are naive, as both are utc and calculated only for this check, plus accuracy is not
            # too important here.
            if last_updated_datetime > stale_feed_date:
                return False
        except Exception as e:
            app.logger.error(e)
            return True
    return True


async def fetch_feedly(query: str) -> List[URL]:
    feed_urls = []

    params = {"query": query}
    headers = {"user-agent": app.config.get("USER_AGENT")}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            "https://cloud.feedly.com/v3/search/feeds", params=params
        ) as resp:
            if resp.status != 200:
                return []

            result = await resp.json()

            stale_feed_date = datetime.utcnow() - timedelta(weeks=12)

            for result in result.get("results"):
                if is_stale_feed(result.get("lastUpdated"), stale_feed_date):
                    continue

                try:
                    url = result.get("feedId").lstrip("feed/")
                    feed_urls.append(URL(url))
                except:
                    pass

    return feed_urls


def fetch_feedly_feeds(query: str) -> List[URL]:
    try:
        feed_urls = asyncio.run(fetch_feedly(query))
        return feed_urls
    except Exception as e:
        app.logger.exception("Search error: %s", e)
        return []
