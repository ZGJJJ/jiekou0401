from flask import Flask
from api.routes import api_bp  # 修改导入路径
from config.settings import FLASK_ENV
import os

# 设置环境
os.environ['FLASK_ENV'] = FLASK_ENV

def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)