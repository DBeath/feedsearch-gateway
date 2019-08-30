import pytest
from gateway.schema import FeedInfoSchema, SiteFeedSchema
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def feedinfo_schema_many():
    return FeedInfoSchema(many=True)


@pytest.fixture(scope="session")
def feedinfo_schema():
    return FeedInfoSchema()


@pytest.fixture(scope="session")
def sitefeed_schema():
    return SiteFeedSchema()


@pytest.fixture(scope="session")
def sitefeed_json():
    with open(BASE_DIR + "/xkcd.com.json") as f:
        json_data = f.read()
    return json_data
