from flask import Flask, request, jsonify, render_template
from flask_s3 import FlaskS3
from feedsearch import search
from feedsearch.lib import coerce_url
from .feedinfo_schema import FEED_INFO_SCHEMA
import json
import time

app = Flask(__name__)
app.config['FLASKS3_BUCKET_NAME'] = 'zappa-mrxw2pac1'
s3 = FlaskS3(app)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_api():
    url = request.args.get('url')
    render_result = request.args.get('result')
    show_time = request.args.get('time')

    if not url:
        response = jsonify({'error': 'No URL in Request'})
        response.status_code = 400
        return response

    start_time = time.perf_counter()

    feed_list = search(url, info=True)

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
