import sqlite3
import os

# 数据库文件放在项目根目录
DB_PATH = r'D:\KPOPproject\kpop_demo.db'

# 如果已存在就删除重建（演示用）
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT,
    title TEXT,
    author TEXT,
    view_count INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    phase TEXT,
    publish_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

print("✅ SQLite数据库创建成功！路径:", DB_PATH)
conn.commit()
cursor.close()
conn.close()