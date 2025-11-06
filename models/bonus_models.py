# models/bonus_models.py
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, SmallInteger
from sqlalchemy.sql import func
from database import Base

class BonusTransaction(Base):
    """Lưu lịch sử giao dịch tặng Loyalty Points"""
    __tablename__ = "bonus_transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, comment="User ID")
    msisdn = Column(String(20), nullable=False, comment="Số điện thoại")
    
    # Transaction info
    ref_trans_id = Column(String(100), unique=True, nullable=False, comment="RefTransId của partner")
    mytel_trans_id = Column(String(100), nullable=True, comment="TransId từ Mytel")
    mytel_loyalty_id = Column(String(100), nullable=True, comment="RefLoyaltyId từ Mytel")
    
    # Reward info
    reward_type = Column(String(20), default="LOYALTY", comment="Loại: LOYALTY, DATA, SMS, VOICE")
    package_code = Column(String(50), nullable=False, comment="LOYALTY_300, LOYALTY_1000, etc")
    points = Column(Integer, nullable=False, comment="Số điểm loyalty")
    
    # Status
    status = Column(String(20), nullable=False, comment="SUCCESS, FAIL, PENDING, WAITING")
    error_message = Column(Text, nullable=True, comment="Error message nếu thất bại")
    note = Column(Text, nullable=True, comment="Ghi chú")
    
    # Source tracking
    source = Column(String(50), nullable=True, comment="Nguồn: GAME_REWARD, DAILY_LOGIN, ACHIEVEMENT, etc")
    source_id = Column(String(100), nullable=True, comment="ID của nguồn")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True, comment="Thời gian hoàn thành giao dịch")