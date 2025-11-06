from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

class ShopItemBase(BaseModel):
    codename: str
    item_name: str
    base_amount: int
    sales_percent: Optional[Decimal] = 0.00
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0

class ShopItemCreate(ShopItemBase):
    pass

class ShopItemUpdate(BaseModel):
    base_amount: Optional[int] = None
    sales_percent: Optional[Decimal] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

class ShopItemResponse(ShopItemBase):
    id: int
    final_amount: int
    on_sale: bool
    
    class Config:
        from_attributes = True

class PurchaseRequest(BaseModel):
    user_id: str
    codename: str
    user_coins: int

class PurchaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None