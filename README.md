# feedsearch-gateway

Serverless AWS API using [Zappa](https://github.com/Miserlou/Zappa) for the [Feedsearch Python package](https://github.com/DBeath/feedsearch).

Live at [Feedsearch](https://feedsearch.auctorial.com/)

## Setup

Install [Pipenv](https://docs.pipenv.org/en/latest/install/#installing-pipenv).

[Install](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) and [configure](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) the AWS CLI.

The following environment variables are required:

```bash
USER_AGENT="The HTTP user agent"
FLASK_S3_BUCKET_NAME="The name of the S3 bucket to serve static files"
DYNAMODB_TABLE="The name of the dynamodb table for storing found feeds"
```

For local development, add the environment variables to a `.env` file.

For production or testing in AWS, add them to the Environment Variables in Lambda.

Update the settings in the `zappa_settings.json` file.

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

