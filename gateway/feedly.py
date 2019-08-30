import aiohttp
from yarl import URL
from datetime import datetime, timedelta, timezone
from flask import current_app as app


async def fetch_feedly(query: str):
    feed_urls = []

    params = {"query": query}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://cloud.feedly.com/v3/search/feeds", params=params
        ) as resp:
            if resp.status != 200:
                return []

            result = await resp.json()

            stale_feed_date = datetime.now() - timedelta(weeks=12)

            for result in result.get("results"):
                last_updated = result.get("lastUpdated")
                if last_updated:
                    try:
                        last_updated_datetime = datetime.utcfromtimestamp(
                            last_updated // 1000
                        )
                        if last_updated_datetime < stale_feed_date:
                            continue
                    except Exception as e:
                        app.logger.error(e)
                        continue
                url = result.get("feedId").lstrip("feed/")
                feed_urls.append(URL(url))

    return feed_urls
