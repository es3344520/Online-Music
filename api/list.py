import os
import json
import boto3
from botocore.client import Config

# 从环境变量读取（Vercel 设置）
ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET = os.environ.get("R2_BUCKET_NAME", "music")

# 音频扩展名
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"}

# 初始化 S3 客户端
s3 = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def parse_filename(filename):
    """解析文件名：支持 '艺术家 - 标题' 或 '艺术家_标题'"""
    name = filename.rsplit(".", 1)[0]  # 去掉扩展名

    if " - " in name:
        parts = name.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    elif "_" in name:
        parts = name.split("_", 1)
        return parts[0].strip(), parts[1].strip()
    else:
        return "Unknown", name.strip()


class handler:
    def do_GET(self):
        from urllib.parse import parse_qs, urlparse

        try:
            # 获取页码参数
            query = parse_qs(urlparse(self.path).query)
            page = int(query.get("page", ["1"])[0])
            page_size = 10

            # 拉取 R2 全部文件（分页拉取，防止单次请求过大）
            all_objects = []
            continuation_token = None

            while True:
                params = {"Bucket": BUCKET, "MaxKeys": 1000}
                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = s3.list_objects_v2(**params)

                for obj in response.get("Contents", []):
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

                if not response.get("IsTruncated"):
                    break
                continuation_token = response.get("NextContinuationToken")

            # 按文件名排序
            all_objects.sort(key=lambda x: x["file"])

            # 分页
            total = len(all_objects)
            total_pages = max(1, (total + page_size - 1) // page_size)
            page = max(1, min(page, total_pages))  # 限制页码范围

            start = (page - 1) * page_size
            end = start + page_size
            page_songs = all_objects[start:end]

            # 返回 JSON
            response_body = {
                "page": page,
                "total_pages": total_pages,
                "total": total,
                "page_size": page_size,
                "songs": page_songs,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_body, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
