import os
import json
import boto3
from botocore.config import Config
from urllib.parse import urlparse

# 初始化R2客户端
def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

def handler(request):
    """Vercel Serverless Function入口"""
    bucket = os.environ['R2_BUCKET_NAME']
    client = get_r2_client()
    
    # 获取查询参数
    page = int(request.query.get('page', 1))
    limit = int(request.query.get('limit', 10))
    file_key = request.query.get('file', '')
    
    # 如果是获取播放链接
    if file_key:
        try:
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': file_key},
                ExpiresIn=3600  # 1小时有效
            )
            return {
                'statusCode': 200,
                'body': json.dumps({'url': url})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    # 获取文件列表（分页）
    try:
        marker = None
        if page > 1:
            # 获取上一页的最后一个文件作为marker
            prev_list = client.list_objects_v2(
                Bucket=bucket,
                MaxKeys=(page-1)*limit
            )
            if 'Contents' in prev_list and len(prev_list['Contents']) > 0:
                marker = prev_list['Contents'][-1]['Key']
        
        response = client.list_objects_v2(
            Bucket=bucket,
            MaxKeys=limit,
            StartAfter=marker if marker else None
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                # 只返回音乐文件（根据扩展名过滤）
                key = obj['Key']
                if key.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg')):
                    files.append({
                        'name': key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
        
        # 判断是否有下一页
        has_more = response.get('IsTruncated', False)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'files': files,
                'page': page,
                'has_more': has_more,
                'total': len(files)
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
