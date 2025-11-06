# schemas/bonus_schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime

class AddLoyaltyRequest(BaseModel):
    """Request để tặng loyalty points"""
    user_id: int = Field(..., description="User ID")
    msisdn: str = Field(..., description="Số điện thoại (959xxxxxxxxx)")
    points: int = Field(..., description="Số điểm loyalty (300, 500, 700, 1000, ...)")
    source: Optional[str] = Field("MANUAL", description="Nguồn: GAME_REWARD, DAILY_LOGIN, etc")
    source_id: Optional[str] = Field(None, description="ID của nguồn")
    note: Optional[str] = Field(None, description="Ghi chú")
    
    @validator('msisdn')
    def validate_msisdn(cls, v):
        if not v.startswith('959'):
            raise ValueError('Phone number must start with 959')
        if len(v) not in [11, 12]:
            raise ValueError('Phone number must be 11 or 12 digits')
        return v
    
    @validator('points')
    def validate_points(cls, v):
        valid_points = [300, 500, 700, 1000, 1500, 2000, 4500, 7000, 8000, 10000]
        if v not in valid_points:
            raise ValueError(f'Points must be one of: {valid_points}')
        return v

class AddLoyaltyResponse(BaseModel):
    """Response sau khi tặng loyalty points"""
    success: bool
    ref_trans_id: str
    mytel_trans_id: Optional[str] = None
    mytel_loyalty_id: Optional[str] = None
    status: str  # SUCCESS, FAIL, PENDING
    message: str
    points: int
    msisdn: str
    
class BonusTransactionResponse(BaseModel):
    """Response cho bonus transaction"""
    id: int
    user_id: int
    msisdn: str
    ref_trans_id: str
    mytel_trans_id: Optional[str]
    mytel_loyalty_id: Optional[str]
    reward_type: str
    package_code: str
    points: int
    status: str
    error_message: Optional[str]
    note: Optional[str]
    source: Optional[str]
    source_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class SearchTransactionRequest(BaseModel):
    """Request tìm kiếm transaction"""
    trans_id: Optional[str] = Field(None, description="Mytel transaction ID")
    ref_id: Optional[str] = Field(None, description="Partner reference ID")
    
    @validator('trans_id', 'ref_id')
    def at_least_one_id(cls, v, values):
        if not v and not values.get('trans_id') and not values.get('ref_id'):
            raise ValueError('Either trans_id or ref_id must be provided')
        return v