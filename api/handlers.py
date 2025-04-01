from flask import request, jsonify
from ..core.database import pg_pool
from datetime import datetime

def handle_usage():
    """处理使用统计查询的业务逻辑"""
    try:
        # 1. 验证API密钥
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "缺少API密钥"}), 401

        # 2. 获取请求参数
        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        group_by = data.get('group_by', 'day')  # 默认按天分组
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        product_type = data.get('product_type')  # 可选的产品类型筛选

        # 3. 验证分组参数
        valid_group_by = ['hour', 'day', 'month', 'year']
        if group_by not in valid_group_by:
            return jsonify({
                "error": f"Invalid group_by parameter. Must be one of: {', '.join(valid_group_by)}"
            }), 400

        # 4. 构建基础查询
        if group_by == 'hour':
            time_group = "DATE_TRUNC('hour', request_time)"
        elif group_by == 'day':
            time_group = "DATE_TRUNC('day', request_time)"
        elif group_by == 'month':
            time_group = "DATE_TRUNC('month', request_time)"
        else:  # year
            time_group = "DATE_TRUNC('year', request_time)"

        query = f"""
            SELECT 
                {time_group} as time_period,
                product_type,
                COUNT(*) as total_calls,
                SUM(data_count) as total_records,
                SUM(credit_used) as total_credits,
                MIN(request_time) as period_start,
                MAX(request_time) as period_end
            FROM api_usage_logs
            WHERE api_key = %s
        """

        # 5. 准备查询参数
        params = [api_key]

        # 添加日期过滤
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND request_time >= %s"
                params.append(start_date)
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                query += " AND request_time <= %s"
                params.append(end_date)
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

        # 添加产品类型过滤
        if product_type:
            query += " AND product_type = %s"
            params.append(product_type)

        # 添加分组和排序
        query += f"""
            GROUP BY {time_group}, product_type
            ORDER BY time_period DESC, product_type
        """

        # 6. 执行数据库查询
        conn = pg_pool.getconn()
        cursor = conn.cursor()

        try:
            # 执行查询
            cursor.execute(query, params)

            # 获取列名和结果
            columns = [desc[0] for desc in cursor.description]
            results = []

            # 7. 处理查询结果
            for row in cursor.fetchall():
                result_dict = dict(zip(columns, row))
                # 格式化日期字段
                for date_field in ['time_period', 'period_start', 'period_end']:
                    if date_field in result_dict and result_dict[date_field]:
                        result_dict[date_field] = result_dict[date_field].strftime('%Y-%m-%d %H:%M:%S')
                results.append(result_dict)

            # 8. 计算汇总信息
            summary = {
                'total_calls': sum(r['total_calls'] for r in results),
                'total_records': sum(r['total_records'] for r in results),
                'total_credits': sum(r['total_credits'] for r in results)
            }

            # 获取额度配置信息
            cursor.execute("""
                SELECT 
                    product_type,
                    total_credit,
                    used_credit,
                    (total_credit - used_credit) as remaining_credit
                FROM api_product_credits
                WHERE api_key = %s
                ORDER BY product_type
            """, [api_key])

            credits_info = [dict(zip(
                ['product_type', 'total_credit', 'used_credit', 'remaining_credit'],
                row
            )) for row in cursor.fetchall()]

            # 9. 返回结果
            return jsonify({
                "usage_data": results,
                "summary": summary,
                "credits_info": credits_info,
                "params": {
                    "group_by": group_by,
                    "start_date": start_date,
                    "end_date": end_date,
                    "product_type": product_type
                },
                "total_records": len(results)
            })

        finally:
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


def handle_credit_balance():
    """查询API账号的产品额度情况"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({"error": "缺少API密钥"}), 401

    try:
        conn = pg_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("""
                SELECT 
                    product_type,
                    total_credit,
                    used_credit,
                    (total_credit - used_credit) as remaining_credit,
                    updated_at
                FROM api_product_credits 
                WHERE api_key = %s
                ORDER BY product_type
            """, (api_key,))

        columns = ['product_type', 'total_credit', 'used_credit',
                   'remaining_credit', 'last_updated']
        credits_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return jsonify({
            "api_key": api_key,
            "credits_data": credits_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        pg_pool.putconn(conn)


def _build_usage_query(group_by, start_date=None, end_date=None):
    """构建使用统计查询SQL

    Args:
        group_by (str): 分组方式 ('hour', 'day', 'month', 'year')
        start_date (str, optional): 开始日期
        end_date (str, optional): 结束日期
    """
    if group_by == 'hour':
        return """
            SELECT 
                endpoint,
                year,
                month,
                day,
                hour,
                SUM(success_count) as success_count,
                SUM(fail_count) as fail_count,
                SUM(data_count) as total_data_count,
                SUM(success_count + fail_count) as total_count,
                usage_date
            FROM api_usage 
            WHERE api_key = %s
            AND usage_date >= COALESCE(%s, usage_date)
            AND usage_date <= COALESCE(%s, usage_date)
            GROUP BY endpoint, year, month, day, hour, usage_date
            ORDER BY usage_date DESC, hour DESC
        """
    # 其他group_by选项的查询语句...（与原代码相同）

    elif group_by == 'month':
        query = """
                              SELECT 
                                  endpoint,
                                  year,
                                  month,
                                  SUM(success_count) as success_count,
                                  SUM(fail_count) as fail_count,
                                  SUM(data_count) as total_data_count,
                                  SUM(success_count + fail_count) as total_count,
                                  MIN(usage_date) as month_start,
                                  MAX(usage_date) as month_end
                              FROM api_usage 
                              WHERE api_key = %s
                          """
        if start_date:
            query += " AND usage_date >= %s"
        if end_date:
            query += " AND usage_date <= %s"

        query += """
                              GROUP BY endpoint, year, month
                              ORDER BY year DESC, month DESC
                          """
        return query

    else:  # day 或 year
        if group_by == 'year':
            select_fields = "year"
            group_fields = "year"
        else:  # day
            select_fields = "year, month, day, usage_date"
            group_fields = "year, month, day, usage_date"

        query = f"""
                              SELECT 
                                  endpoint,
                                  {select_fields},
                                  SUM(success_count) as success_count,
                                  SUM(fail_count) as fail_count,
                                  SUM(data_count) as total_data_count,
                                  SUM(success_count + fail_count) as total_count
                              FROM api_usage 
                              WHERE api_key = %s
                          """
        if start_date:
            query += " AND usage_date >= %s"
        if end_date:
            query += " AND usage_date <= %s"

        query += f"""
                              GROUP BY endpoint, {group_fields}
                              ORDER BY {group_fields} DESC
                          """
        return query

