from flask import Flask, request, jsonify, render_template
from feedsearch import search
from .feedinfo_schema import FEED_INFO_SCHEMA

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def run_search():
    url = request.args.get('url')

    feed_list = search(url, info=True)

    result, errors = FEED_INFO_SCHEMA.dump(feed_list)
    if errors:
        app.logger.warning('Dump errors: {0}'.format(errors))
        return '', 500

    return jsonify(result)
