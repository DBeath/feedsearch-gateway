import time

from botocore.exceptions import ClientError
from flask import current_app as app
from typing import List, Dict


def upload_file(client, data, object_key, bucket_name):
    """
    Upload a file to an S3 bucket

    :param client: S3 Client
    :param data: S3 file body
    :param bucket_name: Bucket to upload to
    :param object_key: S3 object name.
    :return: True if file was uploaded, else False
    """
    start = time.perf_counter()
    object_name = f"{bucket_name}/{object_key}"
    app.logger.info("Uploading %s", object_name)
    try:
        client.put_object(
            Body=data,
            Bucket=bucket_name,
            Key=object_key,
            ContentType="application/json",
            ACL="public-read",
        )
        dur = int((time.perf_counter() - start) * 1000)
        app.logger.debug(
            "Uploaded: file=%s duration=%dms bytes=%d", object_name, dur, len(data)
        )
    except ClientError as e:
        app.logger.error(e)
        return False
    return True


def download_file(client, object_key, bucket_name) -> str:
    """
    Download a file from an S3 bucket

    :param client: S3 Client
    :param object_key: S3 object name.
    :param bucket_name: Bucket to download from
    :return: Object body as bytes
    """
    start = time.perf_counter()
    object_name = f"{bucket_name}/{object_key}"
    app.logger.info("Downloading %s", object_name)
    try:
        response = client.get_object(Bucket=bucket_name, Key=object_key)
        body = response["Body"].read()
        dur = int((time.perf_counter() - start) * 1000)
        app.logger.debug(
            "Downloaded: file=%s duration=%dms bytes=%d",
            object_name,
            dur,
            response.get("ContentLength"),
        )
        return body
    except ClientError as e:
        app.logger.error(e)
        return ""


def list_feed_files(client, bucket_name) -> List[Dict]:
    """
    List site feed files stored in an S3 bucket.

    :param client: S3 Client
    :param bucket_name: Name of the S3 bucket
    :return: List of Dictionary objects containing file information
    """
    paginator = client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix="feeds/")
    site_list = []
    for page in page_iterator:
        contents = page.get("Contents")
        if contents:
            for item in contents:
                feed = {
                    "ETag": item.get("ETag"),
                    "Key": item.get("Key"),
                    "Size": item.get("Size"),
                    "LastModified": item.get("LastModified"),
                }
                site_list.append(feed)
    return site_list
