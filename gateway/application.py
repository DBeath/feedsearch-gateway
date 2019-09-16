import json
import logging
import os
import time
from datetime import datetime
from typing import List, Dict

import boto3
import click
import flask_s3
from dateutil.tz import tzutc
from feedsearch_crawler import output_opml
from feedsearch_crawler.crawler import coerce_url
from flask import Flask, jsonify, render_template, request, Response, g, abort
from flask_assets import Environment, Bundle
from flask_s3 import FlaskS3
from marshmallow import ValidationError
from yarl import URL

from gateway.crawl import site_seen_recently, crawl
from gateway.dynamodb_storage import (
    db_list_sites,
    db_load_site_feeds,
    db_save_site_feeds,
)
from gateway.feedly import fetch_feedly_feeds
from gateway.schema import CustomFeedInfo, score_item
from gateway.utils import force_utc, remove_www
from .schema import FeedInfoSchema, SiteFeedSchema

feedsearch_logger = logging.getLogger("feedsearch_crawler")
feedsearch_logger.setLevel(logging.DEBUG)
db_logger = logging.getLogger("dynamodb")
db_logger.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
if not root_logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
    )
    ch.setFormatter(formatter)
    feedsearch_logger.addHandler(ch)
    db_logger.addHandler(ch)

app = Flask(__name__)

app.config["FLASKS3_BUCKET_NAME"] = os.environ["FLASK_S3_BUCKET_NAME"]
app.config["FLASKS3_GZIP"] = True
app.config["FLASKS3_ACTIVE"] = True
app.config["FLASKS3_GZIP_ONLY_EXTS"] = [".css", ".js"]
app.config["FLASKS3_FORCE_MIMETYPE"] = True
app.config["FLASKS3_HEADERS"] = {"Cache-Control": "max-age=2628000"}
app.config["FLASK_ASSETS_USE_S3"] = True

app.config["DAYS_CHECKED_RECENTLY"] = 7
app.config["USER_AGENT"] = os.environ["USER_AGENT"]
app.config["DYNAMODB_TABLE"] = os.environ["DYNAMODB_TABLE"]

if app.config["DEBUG"]:
    app.config["FLASK_ASSETS_USE_S3"] = False
    app.config["ASSETS_DEBUG"] = True
    app.config["FLASKS3_ACTIVE"] = False


s3 = FlaskS3(app)

css_assets = Bundle(
    "normalize.css",
    "skeleton.css",
    "custom.css",
    filters="cssmin",
    output="packed.min.%(version)s.css",
)

assets = Environment(app)
assets.register("css_all", css_assets)

dynamodb = boto3.resource("dynamodb")
db_table = dynamodb.Table(app.config.get("DYNAMODB_TABLE"))

# def get_resource_as_string(name, charset='utf-8'):
#     with app.open_resource(name) as f:
#         return f.read().decode(charset)

# app.jinja_env.globals['get_resource_as_string'] = get_resource_as_string
# app.jinja_env.globals['css_location'] = css_assets.resolve_output()
# print(app.jinja_env.globals['css_location'])


def has_path(url: URL):
    return bool(url.path.strip("/"))


class BadRequestError(Exception):
    status_code = 400
    name = "Bad Request"

    def __init__(self, message=None):
        Exception.__init__(self)
        self.message = message or "Feedsearch cannot handle the provided request."

    def to_dict(self):
        return {"error": self.name, "message": self.message}


@app.errorhandler(BadRequestError)
def handle_bad_request(error):
    if g.get("return_html", False):
        return render_template("error.html", name=error.name, message=error.message)
    else:
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.exception(e)
    message = "Feedsearch encountered a server error."
    if g.get("return_html", False):
        return render_template("error.html", name="Server Error", message=message)
    else:
        response = jsonify({"error": "Server Error", "message": message})
        response.status_code = 500
        return response


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/sites", methods=["GET"])
def list_sites():
    """
    List all site URLs that have saved feed info.
    """
    sites = db_list_sites(db_table)
    return jsonify(sites)


@app.route("/sites/<url>", methods=["GET"])
def get_site_feeds(url):
    """
    Displays the saved feed info for a site url.

    :param url: URL of site
    """
    url = remove_www(url)

    site_feeds = db_load_site_feeds(db_table, url)

    if site_feeds:
        try:
            site_schema = SiteFeedSchema()
            result = site_schema.dump(site_feeds)
        except ValidationError as err:
            app.logger.warning("Dump errors: %s", err.messages)
            return abort(500)

        return jsonify(result)
    else:
        response = jsonify({"message": f"No feed information saved for url {url}"})
        response.status_code = 402
        return response


@app.route("/search", methods=["GET"])
def search_api():
    """
    Returns info about feeds at a URL.
    """
    query = request.args.get("url", "", type=str)
    return_html = str_to_bool(request.args.get("result", "false", type=str))
    show_stats = str_to_bool(request.args.get("stats", "false", type=str))
    info = str_to_bool(request.args.get("info", "true", type=str))
    check_all = str_to_bool(request.args.get("checkall", "false", type=str))
    favicon = str_to_bool(request.args.get("favicon", "true", type=str))
    return_opml = str_to_bool(request.args.get("opml", "false", type=str))
    force_crawl = str_to_bool(request.args.get("force", "false", type=str))
    check_feedly = str_to_bool(request.args.get("feedly", "true", type=str))

    g.return_html = return_html

    if not query:
        raise BadRequestError("No URL in Request")

    start_time = time.perf_counter()

    if "." not in query:
        raise BadRequestError("Invalid URL provided.")

    try:
        url = coerce_url(query)
    except Exception as e:
        app.logger.error("Error parsing URL %s: %s", query, e)
        raise BadRequestError("Unable to parse provided URL")

    searching_path = has_path(url)
    host = remove_www(url.host)

    stats: dict = {}
    crawl_feed_list: List[CustomFeedInfo] = []

    kwargs = {}
    if not info:
        kwargs["only"] = ["url"]
    if not favicon:
        kwargs["exclude"] = ["favicon_data_uri"]

    feed_schema = FeedInfoSchema(many=True, **kwargs)

    load_start = time.perf_counter()
    site_feeds_data = db_load_site_feeds(db_table, host)
    site_feed_list = site_feeds_data.get("feeds", [])
    load_duration = int((time.perf_counter() - load_start) * 1000)
    app.logger.debug(
        "Site DB Load: feeds=%d duration=%d", len(site_feed_list), load_duration
    )

    # Calculate if the site was recently crawled.
    site_crawled_recently = site_seen_recently(
        site_feeds_data.get("last_seen"), app.config.get("DAYS_CHECKED_RECENTLY")
    )

    crawled = False
    # Always crawl the site if the following conditions are met.
    if (
        not site_feeds_data
        or not site_crawled_recently
        or force_crawl
        or searching_path
    ):
        crawl_start_urls: List[URL] = []
        # Fetch feeds from feedly.com
        if check_feedly:
            feedly_feeds: List[URL] = fetch_feedly_feeds(str(url))
            if feedly_feeds:
                app.logger.info("Feedly Feeds: %s", feedly_feeds)
                crawl_start_urls.extend(feedly_feeds)

        # Crawl the start urls
        crawl_feed_list, stats = crawl(url, crawl_start_urls, check_all)
        crawled = True

    now = datetime.now(tzutc())

    feed_dict = {}
    for feed in site_feed_list:
        if feed.is_valid:
            feed_dict[str(feed.url)] = feed

    for feed in crawl_feed_list:
        feed.last_seen = now
        feed_dict[str(feed.url)] = feed

    all_feeds = list(feed_dict.values())

    for feed in all_feeds:
        if feed.last_updated:
            feed.last_updated = force_utc(feed.last_updated)
        feed.score = score_item(feed, url)

    # Only upload new file if crawl occurred.
    if crawled and not app.config.get("DEBUG"):
        save_start = time.perf_counter()
        db_save_site_feeds(db_table, host, now, all_feeds)
        save_duration = int((time.perf_counter() - save_start) * 1000)
        app.logger.info(
            "Site DB Save: feeds=%d duration=%d", len(all_feeds), save_duration
        )

    # If the requested URL has a path component, then only return the feeds found from the crawl.
    if searching_path:
        feed_list = crawl_feed_list
    else:
        feed_list = list(all_feeds)

    search_time = int((time.perf_counter() - start_time) * 1000)
    app.logger.info("Ran search of %s in %dms", url, search_time)

    result: Dict = {}
    if feed_list:
        try:
            dump_start = time.perf_counter()
            result = feed_schema.dump(feed_list)
            dump_duration = int((time.perf_counter() - dump_start) * 1000)
            app.logger.debug(
                "Schema dump: feeds=%d duration=%dms", len(result), dump_duration
            )
        except ValidationError as err:
            app.logger.warning("Dump errors: %s", err.messages)
            abort(500)

    if show_stats:
        result = {"feeds": result, "search_time_ms": search_time, "crawl_stats": stats}

    if return_html:
        return render_template(
            "results.html",
            feeds=feed_list,
            json=get_pretty_print(result),
            url=url,
            stats=get_pretty_print(stats),
        )
    elif return_opml:
        opml_result = output_opml(feed_list).decode("utf-8")
        return Response(opml_result, mimetype="text/xml")

    return jsonify(result)


def get_pretty_print(json_object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


def str_to_bool(string):
    return string.lower() in ("true", "t", "yes", "y", "1")


@app.cli.command("upload")
@click.option("--env", prompt=True, help="Zappa Environment Name")
def upload(env):
    """Uploads static assets to S3."""
    if not env:
        click.echo("Environment must be specified")
        click.Abort()

    with open("zappa_settings.json", "r") as f:
        settings = json.load(f)

    if not settings:
        click.echo("Settings not loaded")
        click.Abort()
        return

    try:
        s3_bucket = settings[env]["s3_bucket"]
        aws_region = settings[env]["aws_region"]
    except AttributeError:
        click.echo("Failed to get details from settings")
        click.Abort()
        return

    session = boto3.Session()
    credentials = session.get_credentials()
    current_credentials = credentials.get_frozen_credentials()

    app.config["FLASKS3_FORCE_MIMETYPE"] = True

    flask_s3.create_all(
        app,
        user=current_credentials.access_key,
        password=current_credentials.secret_key,
        bucket_name=s3_bucket,
        location=aws_region,
        put_bucket_acl=False,
    )
