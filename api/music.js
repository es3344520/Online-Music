const { S3Client, ListObjectsV2Command, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const {
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_CUSTOM_DOMAIN: rawCustomDomain
  } = process.env;

  const R2_CUSTOM_DOMAIN = rawCustomDomain ? rawCustomDomain.trim() : undefined;

  const s3Client = new S3Client({
    region: 'auto',
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: R2_ACCESS_KEY_ID,
      secretAccessKey: R2_SECRET_ACCESS_KEY,
    },
  });

  // 手动解析完整 URL
  const url = new URL(req.url, `http://${req.headers.host}`);
  const action = url.searchParams.get('action');
  const file = url.searchParams.get('file');

  if (!action || action === 'list') {
    const command = new ListObjectsV2Command({ Bucket: R2_BUCKET_NAME });
    const response = await s3Client.send(command);

    const files = response.Contents
      ?.filter(item => !item.Key.endsWith('/'))
      .map(item => item.Key) || [];

    return res.status(200).json({ success: true, files });
  }

  const encodedFile = encodeURIComponent(file);
  const command = new GetObjectCommand({ Bucket: R2_BUCKET_NAME, Key: encodedFile });
  const signedUrl = await getSignedUrl(s3Client, command, { expiresIn: 1800 });

  let finalUrl = signedUrl;
  if (R2_CUSTOM_DOMAIN) {
    const urlObj = new URL(signedUrl);
    urlObj.hostname = R2_CUSTOM_DOMAIN;
    finalUrl = urlObj.toString();
  }

  return res.status(200).json({ success: true, url: finalUrl });
};
