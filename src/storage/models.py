"""
数据模型 - Event Sourcing架构
只存储订单历史记录，不存储持仓快照
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class OrderRecord(Base):
    """订单记录表 - 所有交易的源头真相"""
    __tablename__ = 'order_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_name = Column(String(100), nullable=False, index=True)  # 组合名称
    order_date = Column(Date, nullable=False, index=True)  # 订单日期
    execution_date = Column(Date, nullable=False, index=True)  # 执行日期（实际交易日）
    ticker = Column(String(20), nullable=False)  # 股票代码（如 2800.HK）
    action = Column(String(10), nullable=False)  # Buy / Sell
    quantity = Column(Float, nullable=False)  # 数量
    asset_type = Column(String(20), default='Stock')  # 资产类型
    created_at = Column(DateTime, default=datetime.now)  # 记录创建时间
    
    def __repr__(self):
        return f"<Order({self.order_date} {self.action} {self.ticker} x{self.quantity})>"


def init_database(db_path='history/trading.db'):
    """初始化数据库"""
    from pathlib import Path
    
    # 确保目录存在
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 创建引擎和表
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    
    # 创建Session工厂
    Session = sessionmaker(bind=engine)
    
    return engine, Session
