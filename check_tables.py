import sqlite3

conn = sqlite3.connect(r'D:\KPOPproject\kpop_agent\db.sqlite3')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Django数据库中的表：")
for t in tables:
    print(f"  - {t[0]}")

conn.close()