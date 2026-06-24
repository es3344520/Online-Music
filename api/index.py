import json
import os
import boto3
from botocore.config import Config

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
        
        # 计算起始位置
        start_index = (page - 1) * per_page
        
        # 列出所有对象
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            MaxKeys=per_page,
            StartAfter='' if page == 1 else None
        )
        
        # 如果是第一页，获取所有文件用于计算总数
        if page == 1:
            all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
            total_files = len(all_objects.get('Contents', []))
        else:
            # 获取总数（简单处理，实际项目可以用HeadObject）
            all_objects = s3_client.list_objects_v2(Bucket=bucket_name)
            total_files = len(all_objects.get('Contents', []))
        
        files = []
        if 'Contents' in response:
            # 过滤音乐文件（支持mp3, wav, flac, m4a等）
            music_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
            for obj in response['Contents']:
                key = obj['Key']
                if any(key.lower().endswith(ext) for ext in music_extensions):
                    files.append({
                        'name': key.split('/')[-1] if '/' in key else key,
                        'key': key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
        
        # 计算总页数
        total_pages = (total_files + per_page - 1) // per_page
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'files': files,
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
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
