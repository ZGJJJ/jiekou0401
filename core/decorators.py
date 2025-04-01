from functools import wraps
from flask import request, jsonify
from jwt import decode, ExpiredSignatureError, InvalidTokenError
from config.settings import JWT_SECRET
from core.auth import generate_token
from core.database import pg_pool
from datetime import datetime
# import asyncio
from functools import wraps
from flask import current_app

# JWT验证装饰器
def require_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. 获取访问令牌
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        # 2. 检查令牌是否存在
        if not token:
            return jsonify({
                "error": "Missing JWT token",
                "error_code": "TOKEN_MISSING"  # 明确的错误代码
            }), 401

        try:
            # 3. 验证访问令牌
            payload = decode(token, JWT_SECRET, algorithms=['HS256'])
            if payload.get('type') != 'access':
                return jsonify({
                    "error": "Invalid token type",
                    "error_code": "TOKEN_INVALID"  # 令牌类型错误
                }), 401

            request.current_user = payload['username']
            return f(*args, **kwargs)

        except ExpiredSignatureError:
            # 4. 处理访问令牌过期
            refresh_token = request.headers.get('Refresh-Token')
            if not refresh_token:
                return jsonify({
                    "error": "Access token expired",
                    "error_code": "ACCESS_TOKEN_EXPIRED",  # 访问令牌过期
                    "message": "Please provide refresh token"
                }), 401

            try:
                # 5. 验证刷新令牌
                refresh_payload = decode(refresh_token, JWT_SECRET, algorithms=['HS256'])
                if refresh_payload.get('type') != 'refresh':
                    return jsonify({
                        "error": "Invalid refresh token type",
                        "error_code": "REFRESH_TOKEN_INVALID"  # 刷新令牌类型错误
                    }), 401

                # 6. 生成新令牌并执行原始请求
                new_tokens = generate_token(refresh_payload['username'])
                response = f(*args, **kwargs)

                # 7. 处理响应格式
                if isinstance(response, tuple):
                    response_data = response[0].get_json()
                    status_code = response[1]
                else:
                    response_data = response.get_json()
                    status_code = 200

                # 8. 添加新令牌到响应中
                response_data['new_tokens'] = {
                    'access_token': new_tokens['access_token'],
                    'refresh_token': new_tokens['refresh_token']
                }

                return jsonify(response_data), status_code

            except ExpiredSignatureError:
                # 9. 处理刷新令牌过期
                return jsonify({
                    "error": "Refresh token expired",
                    "error_code": "REFRESH_TOKEN_EXPIRED",  # 刷新令牌过期
                    "message": "Please login again"
                }), 401

            except InvalidTokenError:
                # 10. 处理刷新令牌无效
                return jsonify({
                    "error": "Invalid refresh token",
                    "error_code": "REFRESH_TOKEN_INVALID",  # 刷新令牌无效
                    "message": "Please login again"
                }), 401

        except InvalidTokenError:
            # 11. 处理访问令牌无效
            return jsonify({
                "error": "Invalid token",
                "error_code": "TOKEN_INVALID",  # 访问令牌无效
                "message": "Please login again"
            }), 401

    return decorated

CREDIT_PER_RECORD = 100  # 每条数据消耗100额度

# API调用统计装饰器
def track_product_usage(product_type):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({"error": "缺少API密钥"}), 401

            try:
                conn = pg_pool.getconn()
                cursor = conn.cursor()

                # 检查该API账号是否有该产品的额度配置
                cursor.execute("""
                    SELECT total_credit, used_credit 
                    FROM api_product_credits 
                    WHERE api_key = %s AND product_type = %s
                """, (api_key, product_type))

                credit_info = cursor.fetchone()
                if not credit_info:
                    return jsonify({
                        "error": "未配置产品额度",
                        "product_type": product_type
                    }), 403

                total_credit, used_credit = credit_info

                # 执行API调用
                response = f(*args, **kwargs)

                # 获取响应数据
                if isinstance(response, tuple):
                    response_data = response[0].get_json()
                    status_code = response[1]
                else:
                    response_data = response.get_json()
                    status_code = 200

                # 计算本次调用需要的额度
                data_count = len(response_data.get('data', []))
                required_credit = data_count * CREDIT_PER_RECORD

                # 检查剩余额度是否足够
                if (used_credit + required_credit) > total_credit:
                    return jsonify({
                        "error": "额度不足",
                        "product_type": product_type,
                        "total_credit": total_credit,
                        "used_credit": used_credit,
                        "remaining_credit": total_credit - used_credit,
                        "required_credit": required_credit
                    }), 403

                # 更新额度使用情况
                cursor.execute("""
                    UPDATE api_product_credits 
                    SET used_credit = used_credit + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE api_key = %s AND product_type = %s
                    RETURNING total_credit, used_credit
                """, (required_credit, api_key, product_type))

                new_credit_info = cursor.fetchone()

                # 记录使用日志
                cursor.execute("""
                    INSERT INTO api_usage_logs 
                    (api_key, product_type, data_count, credit_used)
                    VALUES (%s, %s, %s, %s)
                """, (api_key, product_type, data_count, required_credit))

                conn.commit()

                # 在响应中添加额度使用信息
                response_data['credit_info'] = {
                    "product_type": product_type,
                    "data_count": data_count,
                    "credit_used": required_credit,
                    "total_credit": new_credit_info[0],
                    "remaining_credit": new_credit_info[0] - new_credit_info[1],
                    "message": f"本次调用返回{data_count}条数据，消耗{required_credit}额度"
                }

                return jsonify(response_data), status_code

            except Exception as e:
                return jsonify({"error": str(e)}), 500

            finally:
                cursor.close()
                pg_pool.putconn(conn)

        return decorated

    return decorator

#
# def async_track_product_usage(product_type):
#     """异步版本的额度追踪装饰器"""
#
#     def decorator(f):
#         @wraps(f)
#         async def decorated(*args, **kwargs):
#             api_key = request.headers.get('X-API-Key')
#             if not api_key:
#                 return jsonify({"error": "缺少API密钥"}), 401
#
#             try:
#                 # 执行异步API调用
#                 response = await f(*args, **kwargs)
#
#                 # 获取响应数据
#                 if isinstance(response, tuple):
#                     response_data = response[0].get_json()
#                     status_code = response[1]
#                 else:
#                     response_data = response.get_json()
#                     status_code = 200
#
#                 # 计算数据条数和额度
#                 data_count = len(response_data.get('data', []))
#                 credit_used = data_count * 100
#
#                 # 使用异步数据库连接池
#                 async with current_app.async_pg_pool.acquire() as conn:
#                     # 更新额度使用记录
#                     await conn.execute("""
#                         INSERT INTO api_usage_logs
#                         (api_key, product_type, data_count, credit_used, request_time)
#                         VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
#                     """, api_key, product_type, data_count, credit_used)
#
#                     # 更新产品额度
#                     await conn.execute("""
#                         UPDATE api_product_credits
#                         SET used_credit = used_credit + $1,
#                             updated_at = CURRENT_TIMESTAMP
#                         WHERE api_key = $2 AND product_type = $3
#                     """, credit_used, api_key, product_type)
#
#                 # 添加额度信息到响应
#                 response_data['credit_info'] = {
#                     "product_type": product_type,
#                     "data_count": data_count,
#                     "credit_used": credit_used,
#                     "message": f"本次调用返回{data_count}条数据，消耗{credit_used}额度"
#                 }
#
#                 return jsonify(response_data), status_code
#
#             except Exception as e:
#                 return jsonify({"error": str(e)}), 500
#
#         return decorated
#
#     return decorator