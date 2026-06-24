import json
import os
import boto3
from botocore.config import Config

def app(request):
    try:
        # 获取环境变量
        bucket_name = os.environ.get('R2_BUCKET_NAME')
        access_key = os.environ.get('R2_ACCESS_KEY_ID')
        secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        account_id = os.environ.get('R2_ACCOUNT_ID')
        
        if not all([bucket_name, access_key, secret_key, account_id]):
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing R2 configuration'})
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
        
        # 获取分页参数
        query_params = request.get('queryStringParameters', {}) or {}
        page = int(query_params.get('page', 1))
        per_page = 10
        
        # 获取所有对象
        all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
        all_files = all_objects.get('Contents', [])
        
        # 过滤音乐文件
        music_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
        music_files = []
        for obj in all_files:
            key = obj['Key']
            if any(key.lower().endswith(ext) for ext in music_extensions):
                music_files.append({
                    'name': key.split('/')[-1] if '/' in key else key,
                    'key': key,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        # 计算分页
        total_files = len(music_files)
        total_pages = (total_files + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        page_files = music_files[start:end]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'files': page_files,
                'page': page,
                'per_page': per_page,
                'total': total_files,
                'total_pages': total_pages
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
