import os
import json
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import traceback

def get_r2_client():
    """获取R2客户端"""
    try:
        # 检查环境变量
        required_vars = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY']
        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise Exception(f"缺少环境变量: {', '.join(missing)}")
        
        return boto3.client(
            's3',
            endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
    except Exception as e:
        print(f"初始化R2客户端失败: {str(e)}")
        raise

def handler(request, context):
    """Vercel Serverless Function入口"""
    try:
        # 1. 获取参数
        bucket = os.environ.get('R2_BUCKET_NAME')
        if not bucket:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'R2_BUCKET_NAME 未配置'})
            }
        
        # 2. 获取查询参数
        query = request.query if hasattr(request, 'query') else {}
        page = int(query.get('page', 1))
        limit = int(query.get('limit', 10))
        file_key = query.get('file', '')
        
        # 3. 初始化客户端
        try:
            client = get_r2_client()
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'R2客户端初始化失败: {str(e)}'})
            }
        
        # 4. 处理获取播放链接
        if file_key:
            try:
                url = client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': file_key},
                    ExpiresIn=3600
                )
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'url': url})
                }
            except Exception as e:
                print(f"生成预签名URL失败: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': f'生成播放链接失败: {str(e)}'})
                }
        
        # 5. 处理获取文件列表（分页）
        try:
            # 获取文件列表
            response = client.list_objects_v2(
                Bucket=bucket,
                MaxKeys=limit
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    # 只返回音乐文件
                    if key.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac')):
                        files.append({
                            'name': key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat() if 'LastModified' in obj else None
                        })
            
            # 判断是否有更多
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
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"R2错误: {error_code} - {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'R2访问错误: {error_code}'})
            }
        except Exception as e:
            print(f"获取文件列表失败: {str(e)}")
            print(traceback.format_exc())
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'获取文件列表失败: {str(e)}'})
            }
            
    except Exception as e:
        print(f"未处理的错误: {str(e)}")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'服务器错误: {str(e)}'})
        }
