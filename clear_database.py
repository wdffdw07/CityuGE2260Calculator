"""
数据库清理脚本
提供多种清理选项
"""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.storage import DatabaseManager, init_database

DB_PATH = 'history/trading.db'


def delete_database_file():
    """删除数据库文件（最彻底）"""
    db_file = Path(DB_PATH)
    if db_file.exists():
        db_file.unlink()
        print(f"✓ 已删除数据库文件: {DB_PATH}")
        return True
    else:
        print(f"✗ 数据库文件不存在: {DB_PATH}")
        return False


def clear_all_data():
    """清空所有表数据但保留表结构"""
    try:
        engine, Session = init_database(DB_PATH)
        session = Session()
        
        # 删除所有订单记录
        result = session.execute(text("DELETE FROM order_records"))
        count = result.rowcount
        session.commit()
        
        print(f"✓ 已清空 {count} 条订单记录")
        print("✓ 表结构保留")
        
        session.close()
        return True
    except Exception as e:
        print(f"✗ 清空数据失败: {e}")
        return False


def clear_portfolio_data(portfolio_name: str):
    """清空指定组合的数据"""
    try:
        db = DatabaseManager(DB_PATH)
        engine, Session = db.engine, db.Session
        session = Session()
        
        # 删除指定组合的订单记录
        result = session.execute(
            text("DELETE FROM order_records WHERE portfolio_name = :name"),
            {"name": portfolio_name}
        )
        count = result.rowcount
        session.commit()
        
        if count > 0:
            print(f"✓ 已删除组合 '{portfolio_name}' 的 {count} 条订单记录")
        else:
            print(f"✗ 找不到组合 '{portfolio_name}'")
        
        session.close()
        return count > 0
    except Exception as e:
        print(f"✗ 删除组合数据失败: {e}")
        return False


def list_portfolios():
    """列出所有组合"""
    try:
        db = DatabaseManager(DB_PATH)
        portfolios = db.list_portfolios()
        
        if not portfolios:
            print("✗ 数据库为空，没有组合")
            return []
        
        print(f"\n当前组合列表 ({len(portfolios)} 个):")
        print("-" * 60)
        
        for i, name in enumerate(portfolios, 1):
            summary = db.get_portfolio_summary(name)
            print(f"{i}. {name}")
            print(f"   - 订单数: {summary['total_orders']}")
            print(f"   - 时间跨度: {summary['first_date']} → {summary['last_date']}")
            print(f"   - 交易批次: {len(summary['order_dates'])} 天")
            print()
        
        return portfolios
    except Exception as e:
        print(f"✗ 读取组合列表失败: {e}")
        return []


def main():
    """主菜单"""
    print("=" * 60)
    print("📊 数据库清理工具")
    print("=" * 60)
    
    # 检查数据库是否存在
    db_file = Path(DB_PATH)
    if not db_file.exists():
        print(f"\n✗ 数据库文件不存在: {DB_PATH}")
        print("没有需要清理的数据")
        return
    
    print(f"\n数据库位置: {DB_PATH}")
    print(f"文件大小: {db_file.stat().st_size / 1024:.2f} KB")
    
    # 显示菜单
    print("\n清理选项:")
    print("  [1] 删除数据库文件（最彻底，重新开始）")
    print("  [2] 清空所有数据（保留表结构）")
    print("  [3] 删除指定组合的数据")
    print("  [4] 查看组合列表")
    print("  [5] 退出")
    
    choice = input("\n请选择操作 (1/2/3/4/5): ").strip()
    
    if choice == '1':
        print("\n⚠ 警告: 此操作将删除整个数据库文件，所有数据将丢失！")
        confirm = input("确认删除? (yes/no): ").strip().lower()
        if confirm == 'yes':
            delete_database_file()
        else:
            print("✗ 已取消操作")
    
    elif choice == '2':
        print("\n⚠ 警告: 此操作将清空所有组合的订单数据！")
        confirm = input("确认清空? (yes/no): ").strip().lower()
        if confirm == 'yes':
            clear_all_data()
        else:
            print("✗ 已取消操作")
    
    elif choice == '3':
        portfolios = list_portfolios()
        if portfolios:
            portfolio_name = input("\n请输入要删除的组合名称: ").strip()
            if portfolio_name:
                confirm = input(f"确认删除组合 '{portfolio_name}'? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    clear_portfolio_data(portfolio_name)
                else:
                    print("✗ 已取消操作")
    
    elif choice == '4':
        list_portfolios()
    
    elif choice == '5':
        print("\n✓ 退出")
    
    else:
        print("\n✗ 无效选项")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ 用户中断")
    except Exception as e:
        print(f"\n✗ 程序错误: {e}")
        import traceback
        traceback.print_exc()
