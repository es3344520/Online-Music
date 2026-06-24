import os
import json
import boto3
from botocore.client import Config
from urllib.parse import parse_qs, urlparse, unquote

# ========== 配置 ==========
ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET = os.environ.get("R2_BUCKET_NAME", "music")

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"}

s3 = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


# ========== 工具函数 ==========
def parse_filename(filename):
    name = filename.rsplit(".", 1)[0]
    if " - " in name:
        parts = name.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    elif "_" in name:
        parts = name.split("_", 1)
        return parts[0].strip(), parts[1].strip()
    else:
        return "Unknown", name.strip()


def response_json(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data, ensure_ascii=False),
    }


# ========== 接口: /api/list ==========
def handle_list(request):
    try:
        url = urlparse(request.get("path", ""))
        query = parse_qs(url.query)
        page = int(query.get("page", ["1"])[0])
        page_size = 10

        all_objects = []
        continuation_token = None

        while True:
            params = {"Bucket": BUCKET, "MaxKeys": 1000}
            if continuation_token:
                params["ContinuationToken"] = continuation_token

            resp = s3.list_objects_v2(**params)

            for obj in resp.get("Contents", []):
                key = obj["Key"]
                ext = "." + key.split(".")[-1].lower()
                if ext in AUDIO_EXTS:
                    artist, title = parse_filename(key)
                    all_objects.append({
                        "file": key,
                        "title": title,
                        "artist": artist,
                        "size": obj["Size"],
                        "modified": obj["LastModified"].isoformat(),
                    })

            if not resp.get("IsTruncated"):
                break
            continuation_token = resp.get("NextContinuationToken")

        all_objects.sort(key=lambda x: x["file"])

        total = len(all_objects)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        page_songs = all_objects[start:start + page_size]

        return response_json(200, {
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "page_size": page_size,
            "songs": page_songs,
        })

    except Exception as e:
        return response_json(500, {"error": str(e)})


# ========== 接口: /api/play ==========
def handle_play(request):
    try:
        url = urlparse(request.get("path", ""))
        query = parse_qs(url.query)
        file_key = query.get("file", [""])[0]
        file_key = unquote(file_key)

        if not file_key:
            return response_json(400, {"error": "缺少 file 参数"})

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": file_key},
            ExpiresIn=7200,
        )

        return response_json(200, {
            "url": presigned_url,
            "file": file_key,
            "expires_in": 7200,
        })

    except Exception as e:
        return response_json(500, {"error": str(e)})


# ========== Vercel 入口 ==========
def handler(request):
    path = request.get("path", "")

    if path.startswith("/api/list"):
        return handle_list(request)
    elif path.startswith("/api/play"):
        return handle_play(request)
    else:
        return response_json(404, {"error": "Not Found"})
