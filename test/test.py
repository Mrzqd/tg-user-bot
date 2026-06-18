import sqlite3
import os

# 你的 session 文件名
session_file = '526567834831.session'

if not os.path.exists(session_file):
    print(f"❌ 找不到文件: {session_file}")
    exit()

try:
    # 连接 SQLite 数据库
    conn = sqlite3.connect(session_file)
    cursor = conn.cursor()
    
    # 查询所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"✅ 成功读取！文件中包含的表: {tables}")
    print("-" * 30)
    
    # 判断来源
    if 'entities' in tables and 'sent_files' in tables:
        print("🔍 结论: 这是一个 【Telethon】 格式的 session 文件。")
        print("👉 建议: 如果格式没问题但依然卡住等待输入手机号，说明该 session 的登录授权已被 Telegram 官方撤销（掉线了），必须重新登录。")
        
    elif 'peers' in tables:
        print("🔍 结论: 这是一个 【Pyrogram】 格式的 session 文件。")
        print("👉 建议: Telethon 无法读取 Pyrogram 的文件。你需要改用 Pyrogram 库来运行你的代码。")
        
    else:
        print("🔍 结论: 未知格式，或者这是一个尚未登录的空 session。")

    conn.close()
    
except Exception as e:
    print(f"❌ 读取失败，它可能根本不是标准的 SQLite 数据库文件: {e}")