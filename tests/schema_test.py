from datetime import datetime

from gateway.schema import (
    CustomFeedInfo,
    DynamoDbSitePathSchema,
    SitePath,
    DynamoDbSiteSchema,
)


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
