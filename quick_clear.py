"""
快速清空数据库 - 无需确认
直接删除数据库文件，用于快速重置
"""
from pathlib import Path

DB_PATH = 'history/trading.db'

def quick_clear():
    """快速删除数据库文件"""
    db_file = Path(DB_PATH)
    if db_file.exists():
        db_file.unlink()
        print(f"✓ 数据库已清空: {DB_PATH}")
        print("✓ 可以开始新的测试")
    else:
        print(f"✓ 数据库已经是空的")

if __name__ == '__main__':
    quick_clear()
