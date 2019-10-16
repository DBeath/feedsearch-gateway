import json
import logging
import os
import re
import time
from typing import Dict

import boto3
import click
import flask_s3
import sentry_sdk
from feedsearch_crawler import output_opml
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    Response,
    g,
    abort,
    redirect,
    url_for,
)
from flask_assets import Environment, Bundle
from flask_s3 import FlaskS3
from marshmallow import ValidationError
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from gateway.dynamodb_storage import db_list_sites, db_load_site_feeds
from gateway.search import run_search
from gateway.utils import remove_subdomains, coerce_url
from .schema import FeedInfoSchema, SiteFeedSchema

sentry_initialised = False

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

app.config["FLASKS3_BUCKET_NAME"] = os.environ.get("FLASK_S3_BUCKET_NAME", "")
app.config["FLASKS3_GZIP"] = True
app.config["FLASKS3_ACTIVE"] = True
app.config["FLASKS3_GZIP_ONLY_EXTS"] = [".css", ".js"]
app.config["FLASKS3_FORCE_MIMETYPE"] = True
app.config["FLASKS3_HEADERS"] = {"Cache-Control": "max-age=2628000"}
app.config["FLASK_ASSETS_USE_S3"] = True

app.config["DAYS_CHECKED_RECENTLY"] = 7
app.config["USER_AGENT"] = os.environ.get("USER_AGENT", "")
app.config["DYNAMODB_TABLE"] = os.environ.get("DYNAMODB_TABLE", "")
app.config["SENTRY_DSN"] = os.environ.get("SENTRY_DSN", "")

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


def initialise_sentry():
    global sentry_initialised
    if os.environ.get("SENTRY_DSN", "") and not sentry_initialised:
        sentry_sdk.init(
            os.environ.get("SENTRY_DSN"),
            integrations=[AwsLambdaIntegration(), FlaskIntegration()],
        )
        sentry_initialised = True


initialise_sentry()


def unhandled_exceptions(e, event, context):
    initialise_sentry()
    sentry_sdk.capture_exception(e)
    return True  # Prevent invocation retry


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


@app.errorhandler(500)
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


@app.route("/api/v1/sites", methods=["GET"])
def list_sites():
    """
    List all site URLs that have saved feed info.
    """
    sites = db_list_sites(db_table)
    return jsonify(sites)


@app.route("/api/v1/sites/<url>", methods=["GET"])
def get_site_feeds(url):
    """
    Displays the saved feed info for a site url.

    :param url: URL of site
    """
    url = remove_subdomains(url)

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
def orginal_search_api():
    return redirect(url_for("search_api", **request.args))


@app.route("/api/v1/search", methods=["GET"])
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

    if not re.search(r"[a-z0-9]{2,}\.[a-z0-9]{2,}", query):
        raise BadRequestError(
            f"Invalid URL: '{query}' is not supported as a searchable URL."
        )

    try:
        url = coerce_url(query)
    except Exception as e:
        app.logger.error("Error parsing URL %s: %s", query, e)
        raise BadRequestError(f"Invalid URL: Unable to parse '{query}' as a URL.")

    feed_list, stats = run_search(
        db_table,
        url,
        check_feedly=check_feedly,
        force_crawl=force_crawl,
        check_all=check_all,
    )

    search_time = int((time.perf_counter() - start_time) * 1000)
    app.logger.info("Ran search of %s in %dms", url, search_time)

    result: Dict = {}
    if feed_list:
        try:
            kwargs = {}
            if not info:
                kwargs["only"] = ["url"]
            if not favicon:
                kwargs["exclude"] = ["favicon_data_uri"]

            feed_schema = FeedInfoSchema(many=True, **kwargs)

            feed_list = sorted(feed_list, key=lambda x: x.score, reverse=True)
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
