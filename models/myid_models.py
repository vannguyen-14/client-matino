# models/myid_models.py
from sqlalchemy import (
    Column, BigInteger, String, DateTime, Integer, 
    SmallInteger, UniqueConstraint, Text, Enum
)
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


class MyIDCustomer(Base):
    """Bảng khách hàng MyID đang hoạt động"""
    __tablename__ = "myid_customers"
    __table_args__ = (
        UniqueConstraint('msisdn', 'package_name', name='uq_myid_customer_msisdn_package'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    msisdn = Column(String(20), nullable=False, index=True, comment="Số điện thoại")
    info = Column(String(100), default="DK", comment="Mã gói cước (DK, FT, etc)")
    create_date = Column(DateTime, nullable=False, comment="Ngày tạo")
    last_update = Column(
        DateTime, 
        nullable=False, 
        default=datetime.now, 
        onupdate=datetime.now,
        comment="Lần cập nhật cuối"
    )
    channel = Column(String(20), default="0", comment="0:SMS, 1:WAP, 2:WEB, 3:APP, CP:Content Provider")
    current_charged_date = Column(DateTime, nullable=True, comment="Ngày charge hiện tại")
    next_charge_date = Column(DateTime, nullable=True, comment="Ngày charge tiếp theo")
    package_name = Column(String(30), nullable=False, index=True, comment="Tên gói (DAILY, WEEKLY, MONTHLY, FT, etc)")
    price = Column(Integer, default=0, comment="Giá tiền đăng ký (MMK)")
    note = Column(String(255), default="", comment="Ghi chú")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    password = Column(String(50), nullable=True, comment="Mật khẩu xác thực")
    status = Column(
        Enum('inactive', 'active', name='customer_status'),
        nullable=False,
        default='inactive',
        comment="Trạng thái: inactive, active"
    )


class MyIDCustomerHistory(Base):
    """Lịch sử giao dịch MyID"""
    __tablename__ = "myid_customer_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    msisdn = Column(String(20), nullable=False, index=True, comment="Số điện thoại")
    info = Column(String(100), default="DK", comment="Mã gói cước")
    create_date = Column(DateTime, nullable=False, comment="Ngày tạo")
    last_update = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    channel = Column(String(20), default="0", comment="Kênh đăng ký/hủy/gia hạn")
    current_charged_date = Column(DateTime, nullable=True)
    next_charge_date = Column(DateTime, nullable=True)
    package_name = Column(String(30), nullable=False, index=True)
    price = Column(Integer, default=0)
    note = Column(String(255), default="")
    transaction_id = Column(String(100), nullable=True, index=True, comment="ID giao dịch từ MPS")
    mps_command = Column(String(20), nullable=True, comment="Lệnh từ MPS (YES, OFF, 1, 0, MONFEE)")
    created_at = Column(DateTime, server_default=func.now())
    action = Column(String(20), nullable=True, comment="register/renew/cancel/one_time")
    result = Column(SmallInteger, nullable=False, default=0, comment="0=success,1=failed")


class MyIDCustomerCancel(Base):
    """Khách hàng MyID đã hủy"""
    __tablename__ = "myid_customer_cancel"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    msisdn = Column(String(20), nullable=False, index=True)
    info = Column(String(100), default="HUY", comment="Thông tin hủy")
    create_date = Column(DateTime, nullable=True, comment="Ngày tạo ban đầu")
    last_update = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    channel = Column(String(20), default="0")
    status = Column(Integer, nullable=False, default=0, comment="0=success,1=failed")
    password = Column(String(50), nullable=True, comment="Mật khẩu xác thực")
    current_charged_date = Column(DateTime, nullable=True)
    next_charge_date = Column(DateTime, nullable=True)
    package_name = Column(String(30), nullable=False, index=True)
    last_unreg = Column(DateTime, nullable=True, comment="Ngày hủy dịch vụ")
    note = Column(String(255), default="")
    cancel_date = Column(DateTime, nullable=False, comment="Ngày hủy")
    cancel_reason = Column(String(255), nullable=True, comment="Lý do hủy")
    transaction_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class MyIDLogCharging(Base):
    """Log charging MyID - với unique constraint cho transaction_id"""
    __tablename__ = "myid_log_chargings"
    __table_args__ = (
        UniqueConstraint('transaction_id', name='uq_myid_log_txn'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    action = Column(
        Enum('register', 'cancel', 'renew', 'one_time', name='charging_action'),
        nullable=True,
        comment="Loại hành động"
    )
    msisdn = Column(String(20), nullable=False, index=True, comment="Số điện thoại (không có 84)")
    package_code = Column(String(50), nullable=False, index=True, comment="Mã gói (FT, DAILY, etc)")
    reg_datetime = Column(DateTime, nullable=False, default=datetime.now, comment="Thời gian đăng ký")
    sta_datetime = Column(DateTime, nullable=True, comment="Thời gian bắt đầu")
    end_datetime = Column(DateTime, nullable=True, comment="Thời gian kết thúc")
    expire_datetime = Column(DateTime, nullable=True, comment="Thời gian hết hạn")
    channel = Column(String(20), nullable=False, comment="Kênh đăng ký/hủy/gia hạn")
    charge_price = Column(Integer, nullable=True, comment="Giá tiền charge")
    transaction_id = Column(String(100), nullable=True, unique=True, index=True, comment="ID giao dịch từ MPS")
    mps_command = Column(String(20), nullable=True, comment="Lệnh MPS")
    mode = Column(String(20), default="REAL", comment="REAL hoặc PROMOTION")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_success = Column(SmallInteger, default=0, comment="0:Success, 1:Failed")