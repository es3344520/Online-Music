import os
import json
import boto3
from botocore.client import Config
from urllib.parse import unquote

# 环境变量
ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
BUCKET = os.environ.get("R2_BUCKET_NAME", "music")

# S3 客户端
s3 = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


class handler:
    def do_GET(self):
        from urllib.parse import parse_qs, urlparse

        try:
            # 获取文件参数
            query = parse_qs(urlparse(self.path).query)
            file_key = query.get("file", [""])[0]
            file_key = unquote(file_key)

            if not file_key:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "缺少 file 参数"}).encode())
                return

            # 生成预签名 URL（2小时有效）
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": file_key},
                ExpiresIn=7200,
            )

            response_body = {
                "url": presigned_url,
                "file": file_key,
                "expires_in": 7200,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_body).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
