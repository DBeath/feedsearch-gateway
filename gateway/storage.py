import json

import boto3
from botocore.exceptions import ClientError
from flask import current_app as app
import time


def upload_file(client, data, object_key, bucket_name):
    """Upload a file to an S3 bucket

    :param bucket_name: Bucket to upload to
    :param object_key: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    start = time.perf_counter()
    object = f"{bucket_name}/{object_key}"
    app.logger.info("Uploading %s", object)
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
            "Uploaded: file=%s duration=%dms bytes=%d", object, dur, len(data)
        )
    except ClientError as e:
        app.logger.error(e)
        return False
    return True


def download_file(client, object_key, bucket_name):
    start = time.perf_counter()
    object = f"{bucket_name}/{object_key}"
    app.logger.info("Downloading %s", object)
    try:
        response = client.get_object(Bucket=bucket_name, Key=object_key)
        body = response["Body"].read()
        dur = int((time.perf_counter() - start) * 1000)
        app.logger.debug(
            "Downloaded: file=%s duration=%dms bytes=%d",
            object,
            dur,
            response.get("ContentLength"),
        )
        return body
    except ClientError as e:
        app.logger.error(e)
        return None
