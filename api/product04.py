from flask import request, jsonify
from core.database import pg_pool

#产品4 建筑领域启信分

def product04():
    """处理查询请求的业务逻辑"""
    try:
        data = request.json
        company_name = data.get('company_name')
        #     vfname = "ABB(中国)有限公司"
        if not company_name:
            return jsonify({"error": "Missing 'company_name' parameter"}), 400

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("SELECT ename,credit_code,score,rating,business_score,undertake_score,stability_score,"
                       "performance_score,risk_score,performance_appraisal,bad_behavior_3y, "
                       "malicious_events_1y,is_blacklist FROM public.dm_internal_evaluation WHERE ename = %s",
                       (company_name,))

        result = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        return jsonify({"data": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            cursor.close()
            pg_pool.putconn(conn)