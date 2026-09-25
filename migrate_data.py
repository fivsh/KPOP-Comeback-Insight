import sqlite3

# 源数据库（爬虫存的）
src = sqlite3.connect(r'D:\KPOPproject\kpop_demo.db')
# 目标数据库（Django用的）
dst = sqlite3.connect(r'D:\KPOPproject\kpop_agent\db.sqlite3')

src_cur = src.cursor()
dst_cur = dst.cursor()

# 读取爬虫数据
src_cur.execute("SELECT platform, title, author, view_count, likes, phase, publish_time FROM posts")
rows = src_cur.fetchall()

print(f"从爬虫数据库读取到 {len(rows)} 条数据")

# 清空Django旧数据（可选）
dst_cur.execute("DELETE FROM agent_post")
print("已清空Django旧数据")

# 插入新数据
for row in rows:
    dst_cur.execute("""
        INSERT INTO agent_post (platform, title, author, view_count, likes, phase, publish_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, row)

dst.commit()
print(f"✅ 成功导入 {len(rows)} 条真实数据到Django数据库！")

src.close()
dst.close()