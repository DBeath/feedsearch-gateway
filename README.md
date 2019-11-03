# Feedsearch Gateway

Serverless AWS API using [Zappa](https://github.com/Miserlou/Zappa) for the [Feedsearch Crawler Python package](https://github.com/DBeath/feedsearch-crawler).

Live at https://feedsearch.dev

## Setup

Install [Pipenv](https://docs.pipenv.org/en/latest/install/#installing-pipenv).

[Install](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) and [configure](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) the AWS CLI.

The following environment variables are required:

```bash
USER_AGENT="Mozilla/5.0 (compatible; Feedsearch-Crawler; +https://feedsearch.dev)"
FLASK_S3_BUCKET_NAME="feedsearch-bucket"
DYNAMODB_TABLE="feedsearch-table"
SERVER_NAME="feedsearch.dev"
```

- *USER_AGENT* : HTTP [User-Agent](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent) string.
- *FLASK_S3_BUCKET_NAME* : The name of the [S3](https://aws.amazon.com/s3/) bucket that serves static files.
- *DYNAMODB_TABLE* : The name of the [DynamoDB](https://aws.amazon.com/dynamodb/) table for storing found feeds.
- *SERVER_NAME* : The [host url](https://flask.palletsprojects.com/en/1.1.x/config/#SERVER_NAME) of the site.

For local development, add the environment variables to a `.env` file.

For production or testing in AWS, add them to the Environment Variables in Lambda, either directly 
or in in the `zappa_settings.json` file.

Update the [other settings](https://github.com/Miserlou/Zappa#advanced-settings) in the `zappa_settings.json` file as required.

Run the `create_table.py` script.

```bash
python3 scripts/create_table.py
```

## Development

Run the dev server:

```bash
export FLASK_APP=gateway/application.py
export FLASK_DEBUG=true

flask run
```

## Deployment

Deploy with:

```bash
zappa update production
```

Upload static assets to S3:

```bash
export FLASK_APP=gateway/application.py

flask upload
```

