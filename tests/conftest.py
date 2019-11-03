import pytest
from gateway.schema.external_site_schema import ExternalSiteSchema
from gateway.schema.external_feedinfo_schema import ExternalFeedInfoSchema
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def feedinfo_schema_many():
    return ExternalFeedInfoSchema(many=True)


@pytest.fixture(scope="session")
def feedinfo_schema():
    return ExternalFeedInfoSchema()


@pytest.fixture(scope="session")
def sitefeed_schema():
    return ExternalSiteSchema()


@pytest.fixture(scope="session")
def sitefeed_json():
    with open(BASE_DIR + "/xkcd.com.json") as f:
        json_data = f.read()
    return json_data
