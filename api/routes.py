from flask import Blueprint, request, jsonify
from core.decorators import require_jwt, track_product_usage
from api.handlers import handle_usage, handle_credit_balance
from api.product04 import product04
from api.product03 import product03
from api.product02 import product02
from api.product01 import product01
from core.auth import generate_token
from jwt import decode,ExpiredSignatureError,InvalidTokenError
from core.database import pg_pool
from config.settings import JWT_SECRET
import secrets
import hashlib
from core.decorators import track_product_usage
# from quart import Blueprint, request


api_bp = Blueprint('api', __name__)

@api_bp.route('/register', methods=['POST'])
def register():
    try:
        # 1. 获取用户提交的数据
        data = request.json  # 获取POST请求中的JSON数据
        username = data.get('username')
        password = data.get('password')
        refresh_token = request.headers.get('Refresh-Token')

        # 2. 验证数据完整性
        if not username or not password:
            if refresh_token:
                # 使用refresh token重新登录
                try:
                    refresh_payload = decode(refresh_token, JWT_SECRET, algorithms=['HS256'])
                    if refresh_payload.get('type') != 'refresh':
                        return jsonify({
                            "error": "Invalid refresh token type",
                            "error_code": "REFRESH_TOKEN_INVALID"
                        }), 401

                    username = refresh_payload.get('username')
                except ExpiredSignatureError:
                    return jsonify({
                        "error": "Refresh token expired",
                        "error_code": "REFRESH_TOKEN_EXPIRED"
                    }), 401
                except InvalidTokenError:
                    return jsonify({
                        "error": "Invalid refresh token",
                        "error_code": "REFRESH_TOKEN_INVALID"
                    }), 401
            else:
                return jsonify({"error": "Missing username or password"}), 400

        # 3. 生成安全凭证
        # 生成API key和密码哈希
        api_key = secrets.token_hex(32) # 生成64位随机字符的API密钥
        # 对密码进行哈希处理（不存储原始密码）
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # 4. 数据库操作
        conn = pg_pool.getconn()  # 从连接池获取连接
        cursor = conn.cursor()

        try:
            # 验证用户凭证
            cursor.execute("""
                SELECT api_key 
                FROM api_users 
                WHERE username = %s AND (password_hash = %s OR %s IS NULL) AND is_active = true
            """, (username, password_hash, password))

            result = cursor.fetchone()
            # 验证失败
            if not result:
                return jsonify({"error": "Invalid credentials"}), 401

            # 5. 生成JWT token
            tokens = generate_token(username)

            # 6. 返回认证信息
            return jsonify({
                "access_token": tokens['access_token'],
                "refresh_token": tokens['refresh_token'],
                "api_key": result[0]
            })

        finally:
            # 7. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/login', methods=['POST'])
def login():
    try:
        # 1. 获取登录信息
        data = request.json
        username = data.get('username')
        password = data.get('password')

        # 2. 验证数据完整性
        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # 3. 计算密码哈希
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        # 4. 数据库操作
        try:
            # 验证用户凭证
            cursor.execute("""
                SELECT api_key 
                FROM api_users 
                WHERE username = %s AND password_hash = %s AND is_active = true
            """, (username, password_hash))

            result = cursor.fetchone()
            # 验证失败
            if not result:
                return jsonify({"error": "Invalid credentials"}), 401

            # 5. 生成JWT token
            tokens = generate_token(username)

            # 6. 返回认证信息
            return jsonify({
                "access_token": tokens['access_token'],
                "refresh_token": tokens['refresh_token'],
                "api_key": result[0]
            })

        finally:
            # 6. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/query4', methods=['POST'])
@require_jwt
@track_product_usage('product04')
def query4():
    return product04()

@api_bp.route('/query3', methods=['POST'])
@require_jwt
@track_product_usage('product03')
def query3():
    return product03()

@api_bp.route('/query2', methods=['POST'])
@require_jwt
@track_product_usage('product02')
def query2():
    return product02()

# # 异步路由
# @api_bp.route('/product01', methods=['POST'])
# @require_jwt
# @async_track_product_usage('product01')
# async def query1():
#     return product01()

@api_bp.route('/usage', methods=['POST'])
@require_jwt
def usage():
    return handle_usage()

@api_bp.route('/credit/balance', methods=['POST'])
@require_jwt
def credit_balance():
    return handle_credit_balance()