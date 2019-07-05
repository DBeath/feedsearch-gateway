import asyncio
import json
import logging
import time

import click
import flask_s3
from boto3 import Session
from feedsearch_crawler import FeedsearchSpider, sort_urls, output_opml
from flask import Flask, jsonify, render_template, request, Response
from flask_assets import Environment, Bundle
from flask_s3 import FlaskS3

from .feedinfo_schema import FeedInfoSchema

feedsearch_logger = logging.getLogger("feedsearch_crawler")
feedsearch_logger.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
if not root_logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]"
    )
    ch.setFormatter(formatter)
    feedsearch_logger.addHandler(ch)

app = Flask(__name__)

app.config["FLASKS3_BUCKET_NAME"] = "zappa-mrxw2pac1"
app.config["FLASKS3_GZIP"] = True
app.config["FLASKS3_GZIP_ONLY_EXTS"] = [".css", ".js"]
app.config["FLASKS3_FORCE_MIMETYPE"] = True
app.config["FLASKS3_HEADERS"] = {"Cache-Control": "max-age=2628000"}

if not app.config["DEBUG"]:
    app.config["FLASK_ASSETS_USE_S3"] = False

app.config["FLASK_ASSETS_USE_S3"] = False

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

# def get_resource_as_string(name, charset='utf-8'):
#     with app.open_resource(name) as f:
#         return f.read().decode(charset)

# app.jinja_env.globals['get_resource_as_string'] = get_resource_as_string
# app.jinja_env.globals['css_location'] = css_assets.resolve_output()
# print(app.jinja_env.globals['css_location'])


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["GET"])
def search_api():
    url = request.args.get("url", "", type=str)
    render_result = str_to_bool(request.args.get("result", "false", type=str))
    show_stats = str_to_bool(request.args.get("stats", "false", type=str))
    info = str_to_bool(request.args.get("info", "true", type=str))
    check_all = str_to_bool(request.args.get("checkall", "false", type=str))
    favicon = str_to_bool(request.args.get("favicon", "true", type=str))
    opml = str_to_bool(request.args.get("opml", "false", type=str))

    if not url:
        response = jsonify({"error": "No URL in Request"})
        response.status_code = 400
        return response

    start_time = time.perf_counter()

    async def run_crawler():
        spider = FeedsearchSpider(
            try_urls=check_all,
            concurrency=20,
            request_timeout=4,
            total_timeout=10,
            max_retries=0,
            max_depth=5,
            delay=0,
            user_agent="Mozilla/5.0 (compatible; Feedsearch-Crawler; +https://feedsearch.auctorial.com)",
            favicon_data_uri=favicon,
        )

        await spider.crawl(url)
        return spider

    try:
        crawler = asyncio.run(run_crawler())
    except Exception as e:
        app.logger.exception("Search error: %s", e)
        return "Feedsearch Error", 500

    feed_list = sort_urls(list(crawler.items))

    kwargs = {}
    if not info:
        kwargs["only"] = ["url"]

    schema = FeedInfoSchema(many=True, **kwargs)

    result, errors = schema.dump(feed_list)

    search_time = int((time.perf_counter() - start_time) * 1000)

    if errors:
        app.logger.warning("Dump errors: %s", errors)
        return "Feedsearch Error", 500

    stats = crawler.get_stats()

    if show_stats:
        result = {"feeds": result, "search_time_ms": search_time, "stats": stats}

    if render_result:
        return render_template(
            "results.html",
            feeds=feed_list,
            json=get_pretty_print(result),
            url=url,
            stats=get_pretty_print(stats),
        )
    elif opml:
        opml_result = output_opml(feed_list).decode("utf-8")
        return Response(opml_result, mimetype="text/xml")

    return jsonify(result)


def get_pretty_print(json_object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(",", ": "))


def str_to_bool(string):
    return string.lower() in ("true", "t", "yes", "y", "1")


@app.cli.command("upload")
@click.option("--env", prompt=True, help="Environment")
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

    session = Session()
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
