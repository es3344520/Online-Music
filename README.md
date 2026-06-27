R2音乐库，把音乐存储在cloudflare R2  把请求接口部署在Vercel  

为了快速访问，最好是有自己的域名  

Vercel相关的环境变量命名，在Vercel填写好R2相关的令牌，前4个令牌是必须的，R2域名自定义之后可以填写第五个 


R2_ACCOUNT_ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME 
R2_CUSTOM_DOMAIN【非必须】

注意：配置R2的时候不要开启公开访问，为了防止链接盗用，每一次请求都携带签名，且有过期时间，默认有效10分钟，你可以在api/music.js进行配置
