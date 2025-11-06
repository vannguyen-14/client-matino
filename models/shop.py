from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from database import Base

class ShopItem(Base):
    __tablename__ = "shop_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    codename = Column(String(50), unique=True, nullable=False, comment="Tên code trong JSON data")
    item_name = Column(String(100), nullable=False, comment="Tên hiển thị của item")
    base_amount = Column(Integer, nullable=False, default=0, comment="Giá gốc")
    sales_percent = Column(DECIMAL(5,2), default=0.00, comment="Phần trăm giảm giá (0-100)")
    is_active = Column(Boolean, default=True, comment="Item có đang bán không")
    sort_order = Column(Integer, default=0, comment="Thứ tự sắp xếp")
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    @property
    def final_amount(self):
        """Tính giá sau khi giảm giá"""
        return int(self.base_amount * (1 - self.sales_percent / 100))
    
    @property 
    def on_sale(self):
        """Item có đang sale không"""
        return self.sales_percent > 0