import aws4 from 'aws4';
import { URL } from 'url';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const accountId = process.env.R2_ACCOUNT_ID;
    const accessKeyId = process.env.R2_ACCESS_KEY_ID;
    const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
    const bucketName = process.env.R2_BUCKET_NAME;
    const customDomain = process.env.R2_CUSTOM_DOMAIN;

    if (!accountId || !accessKeyId || !secretAccessKey || !bucketName) {
      return res.status(500).json({ success: false, error: 'Missing R2 configuration' });
    }

    const { action, key } = req.query;

    let url;
    if (action === 'list') {
      url = `https://${accountId}.r2.cloudflarestorage.com/${bucketName}/?list-type=2`;
    } else if (action === 'play' && key) {
      const encodedKey = encodeURIComponent(key);
      url = `https://${accountId}.r2.cloudflarestorage.com/${bucketName}/${encodedKey}`;
    } else {
      return res.status(400).json({ success: false, error: 'Missing action or key parameter' });
    }

    const parsedUrl = new URL(url);
    
    const signed = aws4.sign({
      host: parsedUrl.host,
      path: parsedUrl.pathname + parsedUrl.search,
      method: 'GET',
      service: 's3',
      region: 'us-east-1',
      headers: {
        'Host': parsedUrl.host
      }
    }, {
      accessKeyId: accessKeyId,
      secretAccessKey: secretAccessKey
    });

    const signedUrl = `https://${signed.host}${signed.path}`;

    let finalUrl = signedUrl;
    if (customDomain && action === 'play') {
      finalUrl = signedUrl.replace(
        `${accountId}.r2.cloudflarestorage.com/${bucketName}`,
        customDomain
      );
    }

    return res.status(200).json({ success: true, url: finalUrl });

  } catch (error) {
    console.error('Sign error:', error);
    return res.status(500).json({ success: false, error: error.message });
  }
}
