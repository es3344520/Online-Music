const { S3Client, ListObjectsV2Command, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const {
      R2_ACCOUNT_ID,
      R2_ACCESS_KEY_ID,
      R2_SECRET_ACCESS_KEY,
      R2_BUCKET_NAME,
      R2_CUSTOM_DOMAIN
    } = process.env;

    if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY || !R2_BUCKET_NAME) {
      return res.status(500).json({
        success: false,
        message: '服务器配置错误'
      });
    }

    const s3Client = new S3Client({
      region: 'auto',
      endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: R2_ACCESS_KEY_ID,
        secretAccessKey: R2_SECRET_ACCESS_KEY,
      },
    });

    const { action, file } = req.query;

    if (!action || action === 'list') {
      const command = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
      });

      const response = await s3Client.send(command);
      
      const files = response.Contents
        ?.filter(item => !item.Key.endsWith('/'))
        .map(item => item.Key) || [];

      return res.status(200).json({
        success: true,
        files: files
      });
    }

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

      let signedUrl = await getSignedUrl(s3Client, command, {
        expiresIn: 600,
      });

      if (R2_CUSTOM_DOMAIN) {
        const customDomain = R2_CUSTOM_DOMAIN.replace(/^https?:\/\//, '');
        const urlObj = new URL(signedUrl);
        signedUrl = `https://${customDomain}${urlObj.pathname}${urlObj.search}`;
      }

      return res.status(200).json({
        success: true,
        url: signedUrl
      });
    }

    return res.status(400).json({
      success: false,
      message: '无效的 action 参数'
    });

  } catch (error) {
    console.error('API error:', error);
    res.status(500).json({
      success: false,
      message: '服务器错误'
    });
  }
};
