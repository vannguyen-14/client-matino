from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database import get_db
from models.shop import ShopItem
from models.shop_package import ShopPackage, PackageType
from schemas.shop import (
    ShopItemResponse, 
    ShopItemCreate, 
    ShopItemUpdate,
    PurchaseRequest, 
    PurchaseResponse
)
from schemas.shop_package import (
    ShopPackageResponse,
    ShopPackageCreate,
    ShopPackageUpdate
)
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shop", tags=["Shop"])

# ==================== ITEMS ENDPOINTS ====================

@router.get("/", response_model=List[ShopItemResponse])
async def get_all_shop_items(db: AsyncSession = Depends(get_db)):
    """Lấy tất cả items trong shop"""
    try:
        result = await db.execute(
            select(ShopItem)
            .where(ShopItem.is_active == True)
            .order_by(ShopItem.sort_order, ShopItem.id)
        )
        items = result.scalars().all()
        
        logger.info(f"Retrieved {len(items)} shop items")
        return items
        
    except Exception as e:
        logger.error(f"Error fetching shop items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching shop items"
        )

@router.get("/sales", response_model=List[ShopItemResponse])
async def get_sale_items(db: AsyncSession = Depends(get_db)):
    """Lấy items đang sale"""
    try:
        result = await db.execute(
            select(ShopItem)
            .where(ShopItem.is_active == True, ShopItem.sales_percent > 0)
            .order_by(ShopItem.sales_percent.desc(), ShopItem.sort_order)
        )
        items = result.scalars().all()
        
        logger.info(f"Retrieved {len(items)} sale items")
        return items
        
    except Exception as e:
        logger.error(f"Error fetching sale items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching sale items"
        )

@router.get("/item/{codename}", response_model=ShopItemResponse)
async def get_item_by_codename(codename: str, db: AsyncSession = Depends(get_db)):
    """Lấy thông tin 1 item theo codename"""
    try:
        result = await db.execute(
            select(ShopItem)
            .where(ShopItem.codename == codename, ShopItem.is_active == True)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        logger.info(f"Retrieved item: {codename}")
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching item {codename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching item"
        )

@router.post("/items", response_model=ShopItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ShopItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """Tạo item mới (Admin only)"""
    try:
        # Check if codename already exists
        result = await db.execute(
            select(ShopItem).where(ShopItem.codename == item_data.codename)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item with codename '{item_data.codename}' already exists"
            )
        
        # Create new item
        new_item = ShopItem(**item_data.model_dump())
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        
        logger.info(f"Created new item: {new_item.codename}")
        return new_item
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating item: {str(e)}"
        )

@router.put("/update/{codename}", response_model=dict)
async def update_item_pricing(
    codename: str,
    update_data: ShopItemUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật giá và sale của item (Admin only)"""
    try:
        result = await db.execute(
            select(ShopItem).where(ShopItem.codename == codename)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Update fields if provided
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(item, key, value)
            
        await db.commit()
        await db.refresh(item)
        
        logger.info(f"Updated item: {codename}")
        return {
            "success": True,
            "message": "Item updated successfully",
            "data": {
                "codename": item.codename,
                "base_amount": item.base_amount,
                "sales_percent": float(item.sales_percent),
                "final_amount": item.final_amount
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item {codename}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating item"
        )

@router.delete("/items/{codename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    codename: str,
    db: AsyncSession = Depends(get_db)
):
    """Xóa item (Admin only)"""
    try:
        result = await db.execute(
            select(ShopItem).where(ShopItem.codename == codename)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        await db.delete(item)
        await db.commit()
        
        logger.info(f"Deleted item: {codename}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting item {codename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting item"
        )

# ==================== PACKAGES ENDPOINTS ====================

@router.get("/packages", response_model=List[ShopPackageResponse])
async def get_all_packages(
    package_type: Optional[str] = Query(None, description="Filter by type: subscription or onetime"),
    db: AsyncSession = Depends(get_db)
):
    """Lấy tất cả packages (có thể filter theo type)"""
    try:
        query = select(ShopPackage).where(ShopPackage.is_active == True)
        
        if package_type:
            query = query.where(ShopPackage.package_type == package_type)
        
        query = query.order_by(ShopPackage.sort_order, ShopPackage.id)
        
        result = await db.execute(query)
        packages = result.scalars().all()
        
        logger.info(f"Retrieved {len(packages)} packages (type: {package_type or 'all'})")
        return packages
        
    except Exception as e:
        logger.error(f"Error fetching packages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching packages"
        )

@router.get("/packages/{package_id}", response_model=ShopPackageResponse)
async def get_package_by_id(
    package_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Lấy thông tin 1 package theo ID"""
    try:
        result = await db.execute(
            select(ShopPackage).where(ShopPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package not found"
            )
        
        logger.info(f"Retrieved package: {package_id}")
        return package
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching package {package_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching package"
        )

@router.post("/packages", response_model=ShopPackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    package_data: ShopPackageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Tạo package mới (Admin only)"""
    try:
        new_package = ShopPackage(**package_data.model_dump())
        db.add(new_package)
        await db.commit()
        await db.refresh(new_package)
        
        logger.info(f"Created new package: {new_package.package_name}")
        return new_package
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating package: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating package: {str(e)}"
        )

@router.put("/packages/{package_id}", response_model=ShopPackageResponse)
async def update_package(
    package_id: int,
    update_data: ShopPackageUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật package (Admin only)"""
    try:
        result = await db.execute(
            select(ShopPackage).where(ShopPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package not found"
            )
        
        # Update fields if provided
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(package, key, value)
            
        await db.commit()
        await db.refresh(package)
        
        logger.info(f"Updated package: {package_id}")
        return package
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating package {package_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating package"
        )

@router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    package_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Xóa package (Admin only)"""
    try:
        result = await db.execute(
            select(ShopPackage).where(ShopPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package not found"
            )
        
        await db.delete(package)
        await db.commit()
        
        logger.info(f"Deleted package: {package_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting package {package_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting package"
        )

# ==================== PURCHASE ENDPOINT ====================

@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_item(
    request: PurchaseRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Mua item (kiểm tra coins của user)"""
    try:
        # Lấy thông tin item
        result = await db.execute(
            select(ShopItem)
            .where(ShopItem.codename == request.codename, ShopItem.is_active == True)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return PurchaseResponse(
                success=False,
                message="Item not found"
            )
        
        cost = item.final_amount
        
        # Kiểm tra đủ coins
        if request.user_coins < cost:
            return PurchaseResponse(
                success=False,
                message="Insufficient coins"
            )
        
        # TODO: Cập nhật user coins và inventory trong database
        # Ở đây bạn cần thêm logic cập nhật user data
        
        logger.info(f"User {request.user_id} purchased {request.codename} for {cost} coins")
        
        return PurchaseResponse(
            success=True,
            message="Purchase successful",
            data={
                "item": {
                    "codename": item.codename,
                    "item_name": item.item_name,
                    "cost": cost
                },
                "remaining_coins": request.user_coins - cost
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing purchase: {str(e)}")
        return PurchaseResponse(
            success=False,
            message="Purchase failed"
        )