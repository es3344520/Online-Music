import os
import json
import boto3
from botocore.client import Config
from urllib.parse import unquote

ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET = os.environ.get("R2_BUCKET_NAME", "music")

s3 = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def handler(request):
    from urllib.parse import parse_qs, urlparse

    try:
        url = urlparse(request.get("path", ""))
        query = parse_qs(url.query)
        file_key = query.get("file", [""])[0]
        file_key = unquote(file_key)

        if not file_key:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "缺少 file 参数"}),
            }

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": file_key},
            ExpiresIn=7200,
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "url": presigned_url,
                "file": file_key,
                "expires_in": 7200,
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
