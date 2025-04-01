from flask import request, jsonify
from core.database import pg_pool
import time
import hashlib
import requests
'''
产品3
供应商评价
'''
#
# def product03():
#     try:
#         data = request.json
#         company_name = data.get('company_name')
#         #     vfname = "ABB(中国)有限公司"
#         if not company_name:
#             return jsonify({"error": "Missing 'company_name' parameter"}), 400
#
#         conn = pg_pool.getconn()
#         cursor = conn.cursor()
#
#         cursor.execute("SELECT ename,credit_code,rating,score,business_score,undertake_score"
#                        ",stability_score,performance_score,risk_score,cooperate_count,business_scope,"
#                        "cooperate_amount_avg_3y,cooperate_amount_1y,cooperate_period,"
#                        "cooperate_continuity_3y,performance_appraisal,bad_behavior_3y,"
#                        "malicious_events_1y,is_blacklist FROM public.dm_internal_evaluation WHERE ename = %s",
#                        (company_name,))
#
#         result = cursor.fetchall()
#
#         columns = [desc[0] for desc in cursor.description]
#         data = [dict(zip(columns, row)) for row in result]
#
#         # 调用GET请求
#         url = "https://api.qixin.com/APIService/creditScore/getCreditScore"
#         # 获取当前时间戳（精确到秒）
#         timestamp_seconds = time.time()
#         # 转换为毫秒级别（保留整数部分）
#         timestamp_millis = int(timestamp_seconds * 1000)
#         timestamp = str(timestamp_millis)
#         appkey = "f4ce0084-c4d2-4a7f-9061-cff619895988"
#         secret_key = "51dc9927-71e0-45fe-890d-6bdd904a1581"
#         combined = appkey + timestamp + secret_key
#         #md5加密
#         md5_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()
#         #headers参数
#         headers = {
#             'Auth-Version': '2.0',
#             'appkey': str(appkey),
#             'timestamp': str(timestamp),
#             'sign': str(md5_hash)
#         }
#         #body参数
#         body = {
#             'name': company_name
#         }
#         response = requests.get(url, headers=headers, params=body)
#         print("Response Status Code:", response.status_code)
#
#         external_data = response.json()
#         # 获取data对象中的score，如果不存在则使用默认值0
#         data_dict = external_data.get('data', {})
#         score = data_dict.get('score', None)
#         row_dict = {"external_score": score/10}
#         # 如果data列表中有多个字典，可以考虑合并它们
#         if len(data) > 0:
#             # 先合并external_score
#             combined_data = {**row_dict, **data[0]}
#             # 计算总分（数据库分数和API分数加权求和）
#             total_score =round((combined_data['external_score'] * 0.2) + (float(combined_data['score'])*0.8),2)
#             total_score_dict = {'total_score':total_score}
#             print('total_score',total_score)  #终端验证查看，无实际意义
#             combined_data2 = {**row_dict,**total_score_dict, **data[0]}
#         else:
#             combined_data2 = row_dict
#
#         return jsonify({"data": combined_data2})  #返回json格式
#
#     except Exception as e:   #报错捕捉
#         return jsonify({"error": str(e)}), 500
#
#     finally:
#         if 'conn' in locals():
#             cursor.close()
#             pg_pool.putconn(conn)
def product03():
    try:
        data = request.json
        company_name = data.get('company_name')

        if not company_name:
            return jsonify({"error": "Missing 'company_name' parameter"}), 400

        # 1. 获取内部评估数据
        internal_data = get_internal_evaluation(company_name)
        if not internal_data:
            return jsonify({"error": "未找到公司内部评估数据"}), 404

        # 2. 获取外部评分数据
        external_score = get_external_score(company_name)

        # 3. 计算总分并组合数据
        if internal_data:
            # 添加外部评分
            result_data = {
                **internal_data,
                "external_score": external_score / 10 if external_score else None
            }

            # 计算总分
            if external_score and result_data['score']:
                total_score = round(
                    (result_data['external_score'] * 0.2) +
                    (float(result_data['score']) * 0.8),
                    2
                )
                result_data['total_score'] = total_score

        else:
            result_data = {"external_score": external_score / 10 if external_score else None}

        return jsonify({
            "code": 200,
            "message": "success",
            "data": result_data  # 返回单个字典
        })

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e),
            "data": None
        }), 500


def get_internal_evaluation(company_name):
    """获取内部评估数据"""
    try:
        conn = pg_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                ename,
                credit_code,
                rating,
                score,
                business_score,
                undertake_score,
                stability_score,
                performance_score,
                risk_score,
                cooperate_count,
                business_scope,
                cooperate_amount_avg_3y,
                cooperate_amount_1y,
                cooperate_period,
                cooperate_continuity_3y,
                performance_appraisal,
                bad_behavior_3y,
                malicious_events_1y,
                is_blacklist 
            FROM public.dm_internal_evaluation 
            WHERE ename = %s
        """, (company_name,))

        result = cursor.fetchone()

        if result:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        return None

    finally:
        cursor.close()
        pg_pool.putconn(conn)


def get_external_score(company_name):
    """获取外部评分"""
    url = "https://api.qixin.com/APIService/creditScore/getCreditScore"
    timestamp_millis = int(time.time() * 1000)
    appkey = "f4ce0084-c4d2-4a7f-9061-cff619895988"
    secret_key = "51dc9927-71e0-45fe-890d-6bdd904a1581"

    # 生成签名
    combined = appkey + str(timestamp_millis) + secret_key
    md5_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()

    headers = {
        'Auth-Version': '2.0',
        'appkey': appkey,
        'timestamp': str(timestamp_millis),
        'sign': md5_hash
    }

    params = {'name': company_name}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # 检查响应状态
        external_data = response.json()
        return external_data.get('data', {}).get('score')
    except Exception as e:
        print(f"External API error: {str(e)}")
        return None