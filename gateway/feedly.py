import asyncio
from datetime import datetime, timedelta
from typing import List, Set

import aiohttp
from flask import current_app as app
from yarl import URL

from gateway.utils import truncate_integer, remove_subdomains


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


async def fetch_feedly(query: str) -> List[str]:
    """
    Call the Feedly API for searching feeds, and return the URLs of feeds that have been updated
    in the last 3 months.

    :param query: search query
    :return: List of URLs
    """
    feed_urls: List[str] = []

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
                    feed_id = result.get("feedId", "")
                    if feed_id.startswith("feed/"):
                        feed_id = feed_id[5:]
                    if feed_id:
                        feed_urls.append(feed_id)
                except IndexError:
                    pass

    return feed_urls


def validate_feedly_urls(
    existing_urls: List[str], feedly_urls: List[str], host: str
) -> List[URL]:
    """
    Validate Feedly URLs against the existing URLs and the query host, and return new URLs from Feedly.

    :param existing_urls: List of existing URL strings.
    :param feedly_urls: List of URL strings returned from Feedly.
    :param host: host domain of the query
    :return: List of new URL objects
    """
    new_urls: Set[URL] = set()
    for url in feedly_urls:
        if url not in existing_urls:
            try:
                parsed_url = URL(url)
                if remove_subdomains(parsed_url.host) == host:
                    new_urls.add(parsed_url)
            except Exception as e:
                app.logger.error("URL Parse error: %s", e)

    app.logger.debug("New Feedly urls: %s", new_urls)
    return list(new_urls)


def fetch_feedly_feeds(query: str) -> List[str]:
    """
    Call the Feedly API in an async session, and match returned URLs against existing URLs.

    :param query: The query string
    :return: List of found URL strings
    """
    try:
        feed_urls: List[str] = asyncio.run(fetch_feedly(query))
        app.logger.debug("Feedly urls: %s", feed_urls)
        return feed_urls
    except Exception as e:
        app.logger.exception("Search error: %s", e)
        return []
