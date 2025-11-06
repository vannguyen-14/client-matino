# enhanced_status.py - Cập nhật để sử dụng bảng myid_customers thay vì charging_requests
import logging
from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from datetime import datetime, timedelta
import secrets
import httpx
import json
import base64
from fastapi.responses import JSONResponse, RedirectResponse

from models.models import User, GameStatement
from utils.auth_helper import get_user_from_auth
from utils.response_helper import response_ok, response_error
from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
MYID_API_URL = "http://10.201.203.57:8000/game-common/api/individual/subscription?offset=0&limit=10"
FRONTEND_URL = "https://herosaga.metatekvn.com/herosaga/"

def normalize_msisdn(msisdn: str) -> str:
    """Chuẩn hóa số điện thoại"""
    if not msisdn:
        return msisdn
    msisdn = msisdn.strip()
    if msisdn.startswith("0"):
        msisdn = msisdn[1:]
    return "95" + msisdn

# Thêm model cho MyIDCustomer nếu chưa có
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
import enum

class MyIDCustomerStatus(enum.Enum):
    INACTIVE = 0
    ACTIVE = 1
    PENDING = 2
    CANCELLED = 3

# Temporary model definition - bạn nên move vào models/models.py
class MyIDCustomer:
    __tablename__ = 'myid_customers'
    
    id = Column(Integer, primary_key=True)
    msisdn = Column(String(20), nullable=False)
    info = Column(String(100), default='DK')
    create_date = Column(DateTime, nullable=False)
    last_update = Column(DateTime, nullable=False, default=datetime.utcnow)
    channel = Column(String(20), default='0')
    status = Column(Integer, nullable=False, default=0)  # 0:Inactive, 1:Active, 2:Pending, 3:Cancelled
    current_charged_date = Column(DateTime)
    next_charge_date = Column(DateTime)
    package_name = Column(String(30), nullable=False)
    last_unreg = Column(DateTime)
    last_retry = Column(DateTime)
    price = Column(Integer, default=0)
    note = Column(String(255), default='')
    password = Column(String(50))

def get_package_validity_days(package_name: str) -> int:
    """Trả về số ngày có hiệu lực của gói"""
    package_days = {
        'DAILY': 1,
        'WEEKLY': 7,
        'MONTHLY': 30,
        'VIP_DAILY': 1,
        'VIP_WEEKLY': 7,
        'VIP_MONTHLY': 30,
        'VIP_FOREVER': 36500,  # 100 năm
        'FT': 1  # Free trial 1 ngày
    }
    return package_days.get(package_name.upper(), 1)

async def check_subscription_status(msisdn: str, db: AsyncSession) -> tuple[bool, str]:
    """
    Kiểm tra trạng thái subscription từ bảng myid_customers
    Returns: (can_play: bool, status_message: str)
    """
    try:
        # Query active subscription using SQLAlchemy select
        query = text("""
        SELECT * FROM myid_customers 
        WHERE msisdn = :msisdn 
        AND status = 'active'
        ORDER BY next_charge_date DESC 
        LIMIT 1
        """)
        
        result = await db.execute(query, {"msisdn": msisdn})
        subscription = result.first()
        
        if not subscription:
            logger.info(f"No active subscription found for {msisdn}")
            return False, "NO_SUBSCRIPTION"
        
        logger.info(f"Found subscription: {subscription.package_name}, next_charge: {subscription.next_charge_date}")
        
        # Kiểm tra gói vĩnh viễn
        if subscription.package_name.upper() in ['VIP_FOREVER', 'FOREVER']:
            logger.info("VIP_FOREVER subscription detected")
            return True, "ACTIVE_FOREVER"
        
        # Kiểm tra hạn sử dụng
        if subscription.next_charge_date:
            now = datetime.utcnow()
            if now <= subscription.next_charge_date:
                logger.info(f"Subscription active until {subscription.next_charge_date}")
                return True, "ACTIVE"
            else:
                logger.info(f"Subscription expired at {subscription.next_charge_date}")
                # Cập nhật trạng thái expired
                update_query = text("""
                    UPDATE myid_customers 
                    SET status = 'inactive', note = 'Expired'
                    WHERE id = :sub_id
                """)
                await db.execute(update_query, {"sub_id": subscription.id})
                await db.commit()
                return False, "EXPIRED"
        
        return False, "INVALID_SUBSCRIPTION"
        
    except Exception as e:
        logger.error(f"Error checking subscription: {str(e)}")
        return False, "ERROR"

@router.get("/check-status")
async def check_status(
    auth: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    logger.info("=== CHECK STATUS REQUEST (MYID_CUSTOMERS) ===")
    logger.info(f"Auth token received: {auth[:20]}...")
    
    try:
        user = await get_user_from_auth(auth, db)
        if isinstance(user, JSONResponse):
            logger.error("Auth failed - invalid token")
            return user
            
        logger.info(f"User authenticated: ID={user.id}, MSISDN={user.msisdn}")

        # Lấy statement
        result = await db.execute(select(GameStatement).where(GameStatement.user_id == user.id))
        statement = result.scalars().first()
        if not statement:
            logger.error(f"No game statement found for user {user.id}")
            return JSONResponse(
                status_code=404,
                content=response_error(404, "Game statement not found")
            )
            
        logger.info(f"Game statement found for user {user.id}")

        # Kiểm tra subscription từ bảng myid_customers
        can_play, status_message = await check_subscription_status(user.msisdn, db)
        
        logger.info(f"Subscription check result: can_play={can_play}, status={status_message}")

        response_data = {
            "can_play": can_play,
            "user_id": user.id,
            "token": user.api_token,
            "status": status_message,
            "statement_json": json.loads(statement.statement_json or "{}"),
            "subscription_source": "myid_customers"  # Để debug
        }
        
        logger.info(f"Check status result: can_play={can_play}, status={status_message}")
        logger.info("=== CHECK STATUS COMPLETED ===")
        
        return response_ok(response_data)

    except Exception as e:
        logger.error("=== CHECK STATUS ERROR ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content=response_error(500, f"Internal server error: {str(e)}")
        )

@router.get("/login-myid")
async def login_myid(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    logger.info("=== LOGIN MYID REQUEST ===")
    
    # Log headers và query params
    logger.info("Headers:")
    for k, v in request.headers.items():
        if k.lower() in ['authorization', 'access-token']:
            logger.info(f"  {k}: {v[:20]}...***")
        else:
            logger.info(f"  {k}: {v}")
    
    logger.info("Query Parameters:")
    for k, v in request.query_params.items():
        if k.lower() in ['access-token']:
            logger.info(f"  {k}: {v[:20]}...***")
        else:
            logger.info(f"  {k}: {v}")

    # Lấy thông tin từ headers/query params
    phone_number = request.headers.get("phone-number") or request.query_params.get("phone-number")
    access_token = request.headers.get("access-token") or request.query_params.get("access-token")
    avatar = request.headers.get("avatar") or request.query_params.get("avatar")
    username = request.headers.get("username") or request.query_params.get("username")
    lang = request.headers.get("lang") or request.query_params.get("lang")

    if not phone_number or not access_token:
        logger.error("Missing required fields: phone-number or access-token")
        return JSONResponse(
            status_code=400,
            content=response_error(400, "Missing phone-number or access-token")
        )

    msisdn = normalize_msisdn(phone_number)
    logger.info(f"Normalized MSISDN: {phone_number} -> {msisdn}")

    try:
        # Verify với MyID
        logger.info(f"Calling MyID API: {MYID_API_URL}")
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.get(
                MYID_API_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

        logger.info(f"MyID API Response: Status={resp.status_code}")
        
        if resp.status_code == 401:
            logger.error("MyID token invalid/expired")
            # Redirect về frontend thay vì trả lỗi JSON
            logger.info(f"Redirecting to frontend due to 401: {FRONTEND_URL}")
            return RedirectResponse(url=FRONTEND_URL, status_code=307)

        if resp.status_code != 200:
            logger.error(f"MyID API error: {resp.status_code} - {resp.text}")
            # Redirect về frontend thay vì trả lỗi JSON
            logger.info(f"Redirecting to frontend due to API error: {FRONTEND_URL}")
            return RedirectResponse(url=FRONTEND_URL, status_code=307)

        # Parse response
        try:
            data = resp.json()
            logger.info("MyID response parsed successfully")
        except Exception as parse_error:
            logger.error(f"Failed to parse MyID response: {parse_error}")
            # Redirect về frontend thay vì trả lỗi JSON
            logger.info(f"Redirecting to frontend due to parse error: {FRONTEND_URL}")
            return RedirectResponse(url=FRONTEND_URL, status_code=307)

        result = data.get("result")
        if not result or "content" not in result:
            logger.error(f"Unexpected MyID response format: {data}")
            # Redirect về frontend thay vì trả lỗi JSON
            logger.info(f"Redirecting to frontend due to unexpected format: {FRONTEND_URL}")
            return RedirectResponse(url=FRONTEND_URL, status_code=307)

        subs = result["content"]
        logger.info(f"Found {len(subs)} subscriptions")
        
        # Check verification
        verified = any(
            sub.get("isdn") == msisdn and sub.get("verify")
            for sub in subs
        )

        if not verified:
            logger.error(f"Verification failed for MSISDN: {msisdn}")
            return JSONResponse(
                status_code=401,
                content=response_error(401, "Phone number not verified")
            )

        logger.info(f"MSISDN {msisdn} verified successfully")

        # Tìm/tạo user
        result = await db.execute(select(User).where(User.msisdn == msisdn))
        user = result.scalars().first()

        if not user:
            display_name = username or f"user_{msisdn[-4:]}"
            logger.info(f"Creating new user: {display_name}")
            
            user = User(
                msisdn=msisdn,
                display_name=display_name,
                email=None,
                country=None,
                api_token=secrets.token_hex(32)
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Tạo default statement
            statement = GameStatement(
                user_id=user.id,
                statement_json=json.dumps({
                    "coins": 100,
                    "scores": 0,
                    "name": display_name,
                    "avatar": int(avatar) if avatar and avatar.isdigit() else 0,
                })
            )
            db.add(statement)
            await db.commit()
            logger.info(f"Created new user and statement for {msisdn}")
        else:
            logger.info(f"Found existing user: ID={user.id}")

        if not user.api_token:
            user.api_token = secrets.token_hex(32)
            db.add(user)
            await db.commit()

        # Tạo auth token
        payload = f"{msisdn}:{user.api_token}"
        encoded = base64.urlsafe_b64encode(payload.encode()).decode()
        
        redirect_url = f"{FRONTEND_URL}?auth={encoded}"
        logger.info(f"Redirecting to: {FRONTEND_URL}?auth={encoded[:20]}...")
        logger.info("=== LOGIN MYID COMPLETED ===")
        
        return RedirectResponse(url=redirect_url, status_code=307)

    except Exception as e:
        logger.error("=== LOGIN MYID ERROR ===")
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content=response_error(500, f"Internal server error: {str(e)}")
        )