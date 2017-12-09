import flask_s3
import sys
import json
from boto3 import Session
from gateway.application import app

env = sys.argv[1]
if not env:
    print('Environment must be specified')
    sys.exit()

with open('zappa_settings.json', 'r') as f:
    settings = json.load(f)

if not settings:
    print('Settings not loaded')
    sys.exit()

try:
    s3_bucket = settings[env]['s3_bucket']
    aws_region = settings[env]['aws_region']
except AttributeError:
    print('Failed to get details from settings')
    sys.exit()

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
