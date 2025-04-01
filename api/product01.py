from flask import request, jsonify
from core.database import pg_pool

async def product01():  # 异步视图函数

    # 同步操作：参数处理
    data = request.json  # 同步获取JSON数据
    company_name = data.get('company_name')
    credit_code = data.get('credit_code')

    if not company_name or not credit_code:  # 同步参数校验
        return jsonify({"error": "Missing parameters"}), 400

    # 异步数据库操作
    async with pg_pool.acquire() as conn:  # 异步获取连接
        # 异步执行查询
        rows = await conn.fetch(  # 异步等待查询结果
            "SELECT * FROM public.dm_cooperation WHERE company_name = $1 AND credit_code = $2",
            company_name, credit_code
        )
        # 同步操作：结果转换（Row转dict）
        return jsonify({"data": [dict(row) for row in rows]})  # 同步序列化
