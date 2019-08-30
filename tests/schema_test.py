from gateway.schema import CustomFeedInfo


def test_sitefeed_schema_loads(sitefeed_schema, sitefeed_json):
    sitefeed = sitefeed_schema.loads(sitefeed_json)
    assert sitefeed
    assert isinstance(sitefeed, dict)
    assert sitefeed["host"] == "xkcd.com"
    assert sitefeed["last_checked"]
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


def test_feedinfo_schema_loads():
    pass
