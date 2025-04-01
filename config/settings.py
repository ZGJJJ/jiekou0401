import os
import secrets

# Flask配置
FLASK_ENV = 'development'

# JWT配置
JWT_SECRET = secrets.token_hex(32)

# 数据库配置
# DB_CONFIG = {
#     'host': "10.32.151.4",
#     'port': "5432",
#     'database': "inspur",
#     'user': "inspur",
#     'password': "lcjg$$9999"
# }
DB_CONFIG = {
    'host': "10.32.151.4",
    'port': "5432",
    'database': "inspur",
    'user': "inspur",
    'password': "lcjg$$9999"
}