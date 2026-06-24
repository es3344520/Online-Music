const { S3Client, ListObjectsV2Command, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');

module.exports = async (req, res) => {
  // 设置 CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  // 处理 OPTIONS 预检请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const {
      R2_ACCOUNT_ID,
      R2_ACCESS_KEY_ID,
      R2_SECRET_ACCESS_KEY,
      R2_BUCKET_NAME
    } = process.env;

    // 验证环境变量
    if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY || !R2_BUCKET_NAME) {
      throw new Error('缺少必要的环境变量配置');
    }

    // 初始化 S3 客户端 (兼容 R2)
    const s3Client = new S3Client({
      region: 'auto',
      endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: R2_ACCESS_KEY_ID,
        secretAccessKey: R2_SECRET_ACCESS_KEY,
      },
    });

    // 获取请求参数
    const { action, file } = req.query;

    // 如果没有指定 action，默认为获取列表
    if (!action || action === 'list') {
      // 获取文件列表
      const command = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
      });

      const response = await s3Client.send(command);
      
      // 提取文件名列表
      const files = response.Contents
        ?.filter(item => !item.Key.endsWith('/'))
        .map(item => item.Key) || [];

      return res.status(200).json({
        success: true,
        files: files
      });
    }

    // 生成预签名播放链接
    if (action === 'sign') {
      if (!file) {
        return res.status(400).json({
          success: false,
          message: '缺少 file 参数'
        });
      }

      const command = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: file,
      });

      // 生成预签名链接 (有效期 1 小时)
      const signedUrl = await getSignedUrl(s3Client, command, {
        expiresIn: 3600,
      });

      return res.status(200).json({
        success: true,
        url: signedUrl
      });
    }

    // 未知 action
    return res.status(400).json({
      success: false,
      message: '无效的 action 参数，支持: list, sign'
    });

  } catch (error) {
    console.error('API error:', error);
    res.status(500).json({
      success: false,
      message: error.message || '服务器错误'
    });
  }
};
