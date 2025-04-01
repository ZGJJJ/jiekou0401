import psycopg2
from psycopg2 import pool
from ..config.settings import DB_CONFIG

# PostgreSQL连接池
pg_pool = psycopg2.pool.SimpleConnectionPool(
    1,
    20,
    host=DB_CONFIG['host'],
    port=DB_CONFIG['port'],
    database=DB_CONFIG['database'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password']
)