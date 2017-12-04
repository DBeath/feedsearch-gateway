from flask import Flask, request, jsonify
from feedsearch import search
from feedsearch.feedinfo import FeedInfo
from marshmallow import Schema, fields, post_load

class FeedInfoSchema(Schema):
    url = fields.Url()
    site_url = fields.String(allow_none=True)
    title = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    site_name = fields.String(allow_none=True)
    favicon = fields.String(allow_none=True)
    hub = fields.String(allow_none=True)
    is_push = fields.Boolean(allow_none=True)
    content_type = fields.String(allow_none=True)
    bozo = fields.Integer(allow_none=True)
    version = fields.String(allow_none=True)
    self_url = fields.String(allow_none=True)
    score = fields.Integer(allow_none=True)
    favicon_data_uri = fields.String(allow_none=True)

    @post_load
    def make_feed_info(self, data):
        return FeedInfo(**data)

feedinfoschema = FeedInfoSchema(many=True)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return 'Hello World!', 200

@app.route('/', methods=['POST'])
def run_search():
    url = request.args.get('url')
    print(url)
    feed_list = search(url, info=True)

    result, errors = feedinfoschema.dump(feed_list)
    if errors:
        app.logger.warning('Dump errors: {0}'.format(errors))
        return '', 500

    print(result)
    return jsonify(result)
