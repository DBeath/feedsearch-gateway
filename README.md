# feedsearch-gateway
Serverless AWS API using [Zappa](https://github.com/Miserlou/Zappa) for the [Feedsearch Python package](https://github.com/DBeath/feedsearch).

Live at [Feedsearch](https://feedsearch.auctorial.com/)

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

## Development

Run the dev server:

```bash
export FLASK_APP=gateway/application.py
export FLASK_DEBUG=true

flask run
```