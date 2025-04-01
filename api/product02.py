from flask import request, jsonify
from ..core.database import pg_pool

'''
产品2
上海建工优质供应商名单
'''
def product02():

    try:
        data = request.json
        statistical_year = data.get('statistical_year')
        province = data.get('province')
        total_bid_amount = data.get('total_bid_amount')
        is_blacklist = data.get('is_blacklist')
   #     vfname = "ABB(中国)有限公司"
   #      if not statistical_year:
   #          return jsonify({"error": "Missing 'statistical_year' parameter"}), 400

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        # 构建动态查询条件
        conditions = []
        params = []

        if statistical_year:
            conditions.append("statistical_year = %s")
            params.append(statistical_year)

        if province:
            conditions.append("province = %s")
            params.append(province)

        if total_bid_amount:
            conditions.append("total_bid_amount = %s")
            params.append(total_bid_amount)

        if is_blacklist :
            conditions.append("is_blacklist = %s")
            params.append(is_blacklist)

        # 构建SQL查询
        query = ("SELECT company_name,credit_code,mail_address"
                 ",legal_representative,fax,website,products_type "
                 "FROM public.dm_cooperation")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # 添加排序
        query += " ORDER BY statistical_year DESC"

        # 执行查询
        cursor.execute(query, tuple(params))
        result = cursor.fetchall()

        # 获取列名并转换结果
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        # 添加查询条件到响应
        response = {
            "data": data,
            "query_params": {
                "statistical_year": statistical_year,
                "province": province,
                "total_bid_amount": total_bid_amount,
                "is_blacklist": is_blacklist
            },
            "total_records": len(data)
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "query_params": {
                "statistical_year": statistical_year,
                "province": province,
                "total_bid_amount": total_bid_amount,
                "is_blacklist": is_blacklist
            }
        }), 500

    finally:
        if 'conn' in locals():
            cursor.close()
            pg_pool.putconn(conn)