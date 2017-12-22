# feedsearch-gateway
Serverless AWS API using [Zappa](https://github.com/Miserlou/Zappa) for the [Feedsearch Python package](https://github.com/DBeath/feedsearch).

Live at [Feedsearch](https://feedsearch.auctorial.com/)

## Deployment
Deploy with:

    zappa update production

Upload static assets to S3:

    flask upload
