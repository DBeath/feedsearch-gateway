import os

import boto3
from gateway.dynamodb_storage import db_load_site_path


def test_path_load():
    dynamodb = boto3.resource("dynamodb")
    table_name = "feedsearch-test"
    table = dynamodb.Table(table_name)
    path = "/testing/path"
    site = "arstechnica.com"

    existing = db_load_site_path(table, site, path)
    assert existing
