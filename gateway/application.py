from flask import Flask, request, jsonify, render_template
from flask_s3 import FlaskS3
from feedsearch import search
from .feedinfo_schema import FEED_INFO_SCHEMA
import json

app = Flask(__name__)
app.config['FLASKS3_BUCKET_NAME'] = 'zappa-mrxw2pac1'
s3 = FlaskS3(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')

        feed_list = search(url, info=True)

        return render_template('results.html', feeds=feed_list)

    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_api():
    url = request.args.get('url')

    feed_list = search(url, info=True)

    result, errors = FEED_INFO_SCHEMA.dump(feed_list)
    if errors:
        app.logger.warning('Dump errors: {0}'.format(errors))
        return '', 500

    if request.args.get('result'):
        return render_template('results.html', feeds=get_pretty_print(result), url=url)

    return jsonify(result)

def get_pretty_print(json_object):
    return json.dumps(json_object, sort_keys=True, indent=2, separators=(',', ': '))
