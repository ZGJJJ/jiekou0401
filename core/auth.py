from datetime import datetime, timedelta, timezone
from jwt import encode, decode
from config.settings import JWT_SECRET
import hashlib

# JWT Token生成函数
def generate_token(username):
    # payload是JWT的数据负载，包含我们想要存储在token中的信息
    # 生成访问令牌
    access_payload = {
        'username': username,  # 用户名，可以用来标识是哪个用户
        'exp': datetime.now(timezone.utc) + timedelta(minutes=60),  # 过期时间：当前时间+60min
        'iat': datetime.now(timezone.utc), # token的创建时间（iat = issued at）
        'type': 'access'
    }
    refresh_payload = {
        'username': username,  # 用户名，可以用来标识是哪个用户
        'exp': datetime.now(timezone.utc) + timedelta(days=90),  # 过期时间：当前时间+90天
        'iat': datetime.now(timezone.utc), # token的创建时间（iat = issued at）
        'type': 'refresh'
    }

    # 使用JWT_SECRET密钥对payload进行加密，生成token
    access_token = encode(access_payload, JWT_SECRET, algorithm='HS256')
    refresh_token = encode(refresh_payload, JWT_SECRET, algorithm='HS256')

    return {
        'access_token' : access_token,
        'refresh_token' : refresh_token
    }

def hash_password(password):
    """密码哈希函数"""
    return hashlib.sha256(password.encode()).hexdigest()