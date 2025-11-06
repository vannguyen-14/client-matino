from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from database import Base
import enum

class PackageType(str, enum.Enum):
    """Enum với giá trị lowercase để khớp với DB"""
    SUBSCRIPTION = "subscription"  # Giá trị trong DB
    ONETIME = "onetime"            # Giá trị trong DB

class ShopPackage(Base):
    __tablename__ = "shop_packages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    package_name = Column(String(100), nullable=False, comment="Tên gói")
    
    # FIX: Sử dụng String thay vì Enum để tránh validation strict
    package_type = Column(
        String(20),
        nullable=False, 
        default="onetime", 
        comment="Loại gói: subscription hoặc onetime"
    )
    
    duration_days = Column(Integer, default=0, comment="Số ngày (0 nếu là onetime)")
    price = Column(Integer, nullable=False, comment="Giá tiền (MMK)")
    benefits = Column(Text, comment="Lợi ích của gói")
    description = Column(Text, comment="Mô tả chi tiết")
    is_active = Column(Boolean, default=True, comment="Gói có đang bán không")
    sort_order = Column(Integer, default=0, comment="Thứ tự sắp xếp")
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "package_name": self.package_name,
            "package_type": self.package_type.value if isinstance(self.package_type, PackageType) else self.package_type,
            "duration_days": self.duration_days,
            "price": self.price,
            "benefits": self.benefits,
            "description": self.description,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }