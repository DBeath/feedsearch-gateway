import json
import time

import click
import flask_s3
from boto3 import Session
from feedsearch import search
from feedsearch.lib import coerce_url
from flask import Flask, jsonify, render_template, request
from flask_s3 import FlaskS3
from flask_assets import Environment, Bundle

from .feedinfo_schema import FEED_INFO_SCHEMA

app = Flask(__name__)

app.config['FLASKS3_BUCKET_NAME'] = 'zappa-mrxw2pac1'
app.config['FLASKS3_GZIP'] = True
app.config['FLASKS3_GZIP_ONLY_EXTS'] = ['.css', '.js']
app.config['FLASKS3_FORCE_MIMETYPE'] = True
app.config['FLASKS3_HEADERS'] = {
    'Cache-Control': 'max-age=2628000',
}

if not app.config['DEBUG']:
    app.config['FLASK_ASSETS_USE_S3'] = True

s3 = FlaskS3(app)

css_assets = Bundle(
    'normalize.css',
    'skeleton.css',
    'custom.css',
    filters='cssmin',
    output='packed.min.%(version)s.css'
)

assets = Environment(app)
assets.register('css_all', css_assets)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search_api():
    url = request.args.get('url', '', type=str)
    render_result = str_to_bool(request.args.get('result', 'false', type=str))
    show_time = str_to_bool(request.args.get('time', 'false', type=str))
    info = str_to_bool(request.args.get('info', 'true', type=str))
    check_all = str_to_bool(request.args.get('checkall', 'false', type=str))
    favicon = str_to_bool(request.args.get('favicon', 'false', type=str))

    if not url:
        response = jsonify({'error': 'No URL in Request'})
        response.status_code = 400
        return response

    start_time = time.perf_counter()

    feed_list = search(
        url,
        info=info,
        check_all=check_all,
        favicon_data_uri=favicon
    )

    result, errors = FEED_INFO_SCHEMA.dump(feed_list)

    search_time = int((time.perf_counter() - start_time) * 1000)

    if errors:
        app.logger.warning('Dump errors: %s', errors)
        return '', 500

    if render_result:
        return render_template('results.html',
                               feeds=feed_list,
                               json=get_pretty_print(result),
                               url=coerce_url(url))

    if show_time:
        json_result = {'feeds': result, 'search_time_ms': search_time}
        return jsonify(json_result)

    return jsonify(result)


def get_pretty_print(json_object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(',', ': '))


def str_to_bool(str):
    return str.lower() in ('true', 't', 'yes', 'y', '1')


@app.cli.command('upload')
@click.option('--env', prompt=True, help='Environment')
def upload(env):
    """Uploads static assets to S3."""
    if not env:
        click.echo('Environment must be specified')
        click.Abort()

    with open('zappa_settings.json', 'r') as f:
        settings = json.load(f)

    if not settings:
        click.echo('Settings not loaded')
        click.Abort()

    try:
        s3_bucket = settings[env]['s3_bucket']
        aws_region = settings[env]['aws_region']
    except AttributeError:
        click.echo('Failed to get details from settings')
        click.Abort()

    session = Session()
    credentials = session.get_credentials()
    current_credentials = credentials.get_frozen_credentials()

    app.config['FLASKS3_FORCE_MIMETYPE'] = True

    flask_s3.create_all(app,
                        user=current_credentials.access_key,
                        password=current_credentials.secret_key,
                        bucket_name=s3_bucket,
                        location=aws_region,
                        put_bucket_acl=False)
