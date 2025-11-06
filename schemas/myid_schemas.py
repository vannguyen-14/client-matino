# schemas/myid_schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from enum import Enum


class CustomerStatus(str, Enum):
    inactive = "inactive"
    active = "active"


class ChargingAction(str, Enum):
    """Loại hành động charging"""
    register = "register"
    cancel = "cancel"
    renew = "renew"
    one_time = "one_time"


class MPSBaseRequest(BaseModel):
    """Base schema cho tất cả request từ MPS"""
    username: str
    password: str
    serviceid: str
    msisdn: str
    chargetime: str = Field(..., description="Format: YYYYMMDDHHMISS")
    mode: str = Field(..., description="REAL hoặc PROMOTION")
    amount: str = Field(..., description="Số tiền charge")
    transactionid: str
    
    @validator('msisdn')
    def validate_msisdn(cls, v):
        if v.startswith('959'):
            return v
        elif v.startswith('84959'):
            return v[2:]
        return v
    
    @validator('chargetime')
    def validate_chargetime(cls, v):
        if len(v) not in [12, 14]:
            raise ValueError('chargetime must be in format YYYYMMDDHHMISS')
        return v


class SubRequest(MPSBaseRequest):
    """Schema cho subRequest (đăng ký/hủy qua SMS/USSD)"""
    params: str = Field(..., description="0: REGISTER, 1: CANCEL")
    command: str = Field(..., description="YES/OFF (SMS) hoặc 1/0 (USSD)")
    
    @validator('params')
    def validate_params(cls, v):
        if v not in ['0', '1']:
            raise ValueError('params must be 0 (REGISTER) or 1 (CANCEL)')
        return v


class ResultRequest(MPSBaseRequest):
    """Schema cho resultRequest (gia hạn)"""
    params: str = Field(..., description="0: success, 1: failed")
    command: str = Field(..., description="MONFEE")
    
    @validator('params')
    def validate_params(cls, v):
        if v not in ['0', '1']:
            raise ValueError('params must be 0 (success) or 1 (failed)')
        return v
    
    @validator('command')
    def validate_command(cls, v):
        if v != 'MONFEE':
            raise ValueError('command must be MONFEE for renewal')
        return v


class ContentRequest(MPSBaseRequest):
    """Schema cho contentRequest (mua gói một lần)"""
    params: str = Field(..., description="OTP")
    
    @validator('params')
    def validate_params(cls, v):
        if v != 'OTP':
            raise ValueError('params must be OTP for one-time package')
        return v


class MPSResponse(BaseModel):
    """Response trả về cho MPS"""
    return_code: str = Field(alias="return", default="0", description="0: success, 1: failed")
    
    class Config:
        allow_population_by_field_name = True


# Schemas cho MPS Transactions API
class MPSTransactionFilter(BaseModel):
    """Filter cho MPS transactions"""
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    msisdn: Optional[str] = None
    package_code: Optional[str] = None
    transaction_id: Optional[str] = None
    mps_command: Optional[str] = None
    action: Optional[str] = None
    channel: Optional[str] = None
    is_success: Optional[int] = Field(None, ge=0, le=1)
    mode: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ChargingLogResponse(BaseModel):
    """Schema response log charging"""
    id: int
    action: Optional[str]
    msisdn: str
    package_code: str
    reg_datetime: datetime
    sta_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    expire_datetime: Optional[datetime]
    channel: str
    charge_price: Optional[int]
    transaction_id: Optional[str]
    mps_command: Optional[str]
    mode: str
    is_success: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChargingStatsResponse(BaseModel):
    """Response thống kê charging"""
    total_transactions: int
    success_count: int
    failed_count: int
    success_rate: float
    total_revenue: int
    action_breakdown: dict
    package_breakdown: dict
    channel_breakdown: dict
    mode_breakdown: dict


# Schemas cho internal API
class CustomerCreate(BaseModel):
    """Schema tạo khách hàng mới"""
    msisdn: str
    password: Optional[str] = None
    info: Optional[str] = "DK"
    channel: Optional[str] = "0"
    package_name: str
    price: Optional[int] = 0
    note: Optional[str] = ""
    status: Optional[CustomerStatus] = CustomerStatus.inactive


class CustomerUpdate(BaseModel):
    """Schema cập nhật thông tin khách hàng"""
    info: Optional[str] = None
    channel: Optional[str] = None
    current_charged_date: Optional[datetime] = None
    next_charge_date: Optional[datetime] = None
    price: Optional[int] = None
    note: Optional[str] = None
    status: Optional[CustomerStatus] = None


class CustomerResponse(BaseModel):
    """Schema response khách hàng"""
    id: int
    msisdn: str
    password: Optional[str] = None
    info: str
    create_date: datetime
    last_update: datetime
    channel: str
    status: str
    current_charged_date: Optional[datetime]
    next_charge_date: Optional[datetime]
    package_name: str
    price: int
    note: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChargingLogCreate(BaseModel):
    """Schema tạo log charging"""
    action: Optional[ChargingAction] = None
    msisdn: str
    package_code: str
    reg_datetime: Optional[datetime] = None
    sta_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    expire_datetime: Optional[datetime] = None
    channel: str
    charge_price: Optional[int] = None
    transaction_id: Optional[str] = None
    mps_command: Optional[str] = None
    mode: str = "REAL"
    is_success: Optional[int] = 0


class ChargingLogUpdate(BaseModel):
    """Schema cập nhật log charging"""
    action: Optional[ChargingAction] = None
    sta_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    expire_datetime: Optional[datetime] = None
    is_success: Optional[int] = None