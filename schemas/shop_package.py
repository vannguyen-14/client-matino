from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class PackageTypeEnum(str, Enum):
    SUBSCRIPTION = "subscription"
    ONETIME = "onetime"

class ShopPackageBase(BaseModel):
    package_name: str = Field(..., description="Tên gói")
    package_type: PackageTypeEnum = Field(default=PackageTypeEnum.ONETIME, description="Loại gói")
    duration_days: int = Field(default=0, ge=0, description="Số ngày (0 cho onetime)")
    price: int = Field(..., ge=0, description="Giá tiền MMK")
    benefits: Optional[str] = Field(None, description="Lợi ích")
    description: Optional[str] = Field(None, description="Mô tả")
    is_active: Optional[bool] = Field(True, description="Trạng thái")
    sort_order: Optional[int] = Field(0, description="Thứ tự sắp xếp")

class ShopPackageCreate(ShopPackageBase):
    """Schema for creating new package"""
    pass

class ShopPackageUpdate(BaseModel):
    """Schema for updating package - all fields optional"""
    package_name: Optional[str] = None
    package_type: Optional[PackageTypeEnum] = None
    duration_days: Optional[int] = None
    price: Optional[int] = None
    benefits: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

class ShopPackageResponse(ShopPackageBase):
    """Schema for package response"""
    id: int
    
    class Config:
        from_attributes = True
        orm_mode = True