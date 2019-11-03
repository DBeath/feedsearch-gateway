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
    feed1 = sitefeed["feeds"][0]
    assert feed1
    assert isinstance(feed1, CustomFeedInfo)
    assert feed1.title == "xkcd.com"
    assert feed1.version == "rss20"
    feed2 = sitefeed["feeds"][1]
    assert isinstance(feed2, CustomFeedInfo)
    assert feed2.title == "xkcd.com"
    assert feed2.version == "atom10"


def test_site_schema(sitefeed_json):
    schema = DynamoDbSiteSchema()


def test_feedinfo_schema_loads():
    pass


def test_dynamodb_feedinfo_schema_load():
    value = {
        "PK": "SITE#en.wikipedia.org",
        "SK": "FEED#https://en.wikipedia.org?feed=potd&format=atom",
        "host": "en.wikipedia.org",
        "url": "https://en.wikipedia.org?feed=potd&format=atom",
        "last_seen": "2019-11-03T08:50:43+00:00",
    }
    schema = DynamoDbFeedInfoSchema()
    feed = schema.load(value)
    assert isinstance(feed, CustomFeedInfo)
    assert feed.host == "en.wikipedia.org"
    assert feed.url == URL("https://en.wikipedia.org?feed=potd&format=atom")
    assert feed.last_seen == datetime(2019, 11, 3, 8, 50, 43, tzinfo=tz.tzutc())


def test_dynamodb_site_schema_load():
    value = {
        "PK": "SITE#en.wikipedia.org",
        "SK": "#METADATA#en.wikipedia.org",
        "host": "en.wikipedia.org",
        "last_seen": "2019-11-03T08:50:43+00:00",
    }
    schema = DynamoDbSiteSchema()
    site = schema.load(value)
    assert isinstance(site, SiteHost)
    assert site.host == "en.wikipedia.org"
    assert site.last_seen == datetime(2019, 11, 3, 8, 50, 43, tzinfo=tz.tzutc())


def test_sitepath_schema():
    schema = DynamoDbSitePathSchema()

    feeds = ["test.com/testing/rss.xml", "test.com/testing/atom.xml"]

    sitepath = SitePath(
        host="test.com", path="/testing", last_seen=datetime(2019, 1, 1), feeds=feeds
    )

    serialized = schema.dump(sitepath)
    assert serialized.get("PK") == "SITEPATH#test.com"
    assert serialized.get("SK") == "PATH#/testing"
    assert serialized.get("feeds") == feeds

    deserialized = schema.load(serialized)
    assert isinstance(deserialized, SitePath)
    assert deserialized.host == "test.com"
    assert deserialized.path == "/testing"
    assert deserialized.feeds == feeds
