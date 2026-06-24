import json
import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from urllib.parse import urlparse

def handler(request):
    try:
        # 获取环境变量
        bucket_name = os.environ.get('R2_BUCKET_NAME')
        access_key = os.environ.get('R2_ACCESS_KEY_ID')
        secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        account_id = os.environ.get('R2_ACCOUNT_ID')
        
        if not all([bucket_name, access_key, secret_key, account_id]):
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Missing R2 configuration'})
            }
        
        # 获取文件key
        query_params = request.get('queryStringParameters', {}) or {}
        file_key = query_params.get('file')
        
        if not file_key:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing file parameter'})
            }
        
        # 配置R2客户端
        s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto',
            config=Config(signature_version='s3v4')
        )
        
        # 生成预签名URL（有效期30分钟）
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key
            },
            ExpiresIn=1800  # 30分钟
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'url': presigned_url,
                'file': file_key
            })
        }
        
    except ClientError as e:
        return {
            'statusCode': 403,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Access denied: ' + str(e)})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
