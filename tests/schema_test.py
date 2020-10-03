from datetime import datetime
from decimal import Decimal

from dateutil import tz
from yarl import URL

from gateway.schema.customfeedinfo import CustomFeedInfo
from gateway.schema.dynamodb_feedinfo_schema import DynamoDbFeedInfoSchema
from gateway.schema.dynamodb_site_schema import DynamoDbSiteSchema
from gateway.schema.dynamodb_sitepath_schema import DynamoDbSitePathSchema
from gateway.schema.sitehost import SiteHost
from gateway.schema.sitepath import SitePath


def test_sitefeed_schema_loads(sitefeed_schema, sitefeed_json):
    sitefeed = sitefeed_schema.loads(sitefeed_json)
    assert sitefeed
    assert isinstance(sitefeed, dict)
    assert sitefeed["host"] == "xkcd.com"
    assert sitefeed["last_seen"]
    assert len(sitefeed["feeds"]) == 2
    feed1 = sitefeed["feeds"]["https://xkcd.com/rss.xml"]
    assert feed1
    assert isinstance(feed1, CustomFeedInfo)
    assert feed1.title == "xkcd.com"
    assert feed1.version == "rss20"
    feed2 = sitefeed["feeds"]["https://xkcd.com/atom.xml"]
    assert isinstance(feed2, CustomFeedInfo)
    assert feed2.title == "xkcd.com"
    assert feed2.version == "atom10"


def test_feedinfo_schema_loads():
    pass


feedinfo_schema_dict = {
    "PK": "SITE#en.wikipedia.org",
    "SK": "FEED#https://en.wikipedia.org/?feed=potd&format=atom",
    "bozo": 0,
    "content_length": 1024,
    "host": "en.wikipedia.org",
    "hubs": ["https://pubsubhubbub.com", "https://test.com/hub"],
    "is_podcast": False,
    "is_push": True,
    "item_count": 10,
    "last_seen": "2019-11-03T08:50:43+00:00",
    "score": 0,
    "url": "https://en.wikipedia.org/?feed=potd&format=atom",
    "velocity": 1,
}


def test_dynamodb_feedinfo_schema_load():
    schema = DynamoDbFeedInfoSchema()
    feed = schema.load(feedinfo_schema_dict)
    assert isinstance(feed, CustomFeedInfo)
    assert feed.host == "en.wikipedia.org"
    assert feed.url == URL("https://en.wikipedia.org?feed=potd&format=atom")
    assert feed.last_seen == datetime(2019, 11, 3, 8, 50, 43, tzinfo=tz.tzutc())
    assert feed.hubs == ["https://pubsubhubbub.com", "https://test.com/hub"]
    assert feed.velocity == 1
    assert feed.is_push is True
    assert feed.item_count == 10
    assert feed.content_length == 1024


def test_dynamodb_feedinfo_schema_dump():
    schema = DynamoDbFeedInfoSchema()
    feed = CustomFeedInfo(
        host="en.wikipedia.org",
        url=URL("https://en.wikipedia.org?feed=potd&format=atom"),
        last_seen=datetime(2019, 11, 3, 8, 50, 43, tzinfo=tz.tzutc()),
        hubs=["https://pubsubhubbub.com", "https://test.com/hub"],
        velocity=1,
        is_push=True,
        item_count=10,
        content_length=1024,
    )
    dump = schema.dump(feed)
    assert dump == feedinfo_schema_dict


site_schema_dict = {
    "PK": "SITE#en.wikipedia.org",
    "SK": "#METADATA#",
    "host": "en.wikipedia.org",
    "last_seen": "2019-11-03T08:50:43+00:00",
}


def test_dynamodb_site_schema_load():
    schema = DynamoDbSiteSchema()
    site = schema.load(site_schema_dict)
    assert isinstance(site, SiteHost)
    assert site.host == "en.wikipedia.org"
    assert site.last_seen == datetime(2019, 11, 3, 8, 50, 43, tzinfo=tz.tzutc())


def test_dynamodb_site_schema_dump():
    schema = DynamoDbSiteSchema()
    site = SiteHost(
        host="en.wikipedia.org",
        last_seen=datetime(2019, 11, 3, 8, 50, 43, tzinfo=tz.tzutc()),
    )
    dump = schema.dump(site)
    assert dump == site_schema_dict


def test_sitepath_schema():
    schema = DynamoDbSitePathSchema()

    feeds = ["test.com/testing/rss.xml", "test.com/testing/atom.xml"]

    sitepath = SitePath(
        host="test.com", path="/testing", last_seen=datetime(2019, 1, 1), feeds=feeds
    )

    serialized = schema.dump(sitepath)
    assert serialized.get("PK") == "SITE#test.com"
    assert serialized.get("SK") == "PATH#/testing"
    assert serialized.get("feeds") == feeds

    deserialized = schema.load(serialized)
    assert isinstance(deserialized, SitePath)
    assert deserialized.host == "test.com"
    assert deserialized.path == "/testing"
    assert deserialized.feeds == feeds
