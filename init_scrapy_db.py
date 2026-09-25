import sqlite3
import os

DB_PATH = r'D:\KPOPproject\kpop_demo.db'

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("已删除旧数据库")

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

conn.commit()
conn.close()
print("✅ 爬虫数据库和表创建成功")