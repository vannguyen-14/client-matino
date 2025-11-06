# routers/myid_web_charge.py - Updated for new models/schemas
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from datetime import datetime, timedelta, timezone
import httpx
import logging
from typing import Optional, Literal
from models.myid_models import MyIDCustomer, MyIDLogCharging, MyIDCustomerHistory, MyIDCustomerCancel
from models.models import User
import secrets
from services.myid_crypto import (
    load_private_key, 
    KEY_BASE_PATH,
    encrypt_with_mps_public_key_v2,
    sign_data_v2,
    decrypt_with_mps_private_key_v2
)
from urllib.parse import quote
import time, random

logger = logging.getLogger(__name__)
router = APIRouter()

# ====== Configuration ======
MPS_CONFIG = {
    "base_url": "https://mpsapi.mytel.com.mm/MPS/charge.html",
    "cp_code": "MDC",
    "service_name": "SUPER_MATINO",
    "timeout": 300
}

MPS_HEADERS = {
    "User-Agent": "curl/7.81.0",
    "Accept": "*/*"
}

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

# ====== Request/Response Models ======
class WebChargeRequest(BaseModel):
    msisdn: str = Field(..., description="Số điện thoại (959xxxxxxxxx)")
    cmd: Literal["REGISTER", "CANCEL", "CHARGE"] = Field(..., description="Lệnh thực hiện")
    package_name: str = Field(..., description="Tên gói: DAILY, WEEKLY, MONTHLY, etc")
    channel: str = Field(default="WEB", description="Kênh: WEB hoặc WAP")
    sub_service_name: Optional[str] = Field(None, description="Tên sub-service cụ thể")
    
class WebChargeResponse(BaseModel):
    status: Literal["success", "failed", "user_cancel", "timeout", "pending"]
    message: str
    mps_code: Optional[str] = None
    mps_message: Optional[str] = None
    transaction_id: Optional[str] = None
    expire_datetime: Optional[datetime] = None
    charge_price: Optional[int] = None
    data: Optional[dict] = None

# ====== Package Configuration ======
PACKAGE_CONFIG = {
    "DAILY": {"price": 169, "duration_days": 1, "sub_service": "SUPER_MATINO_DAILY"},
    "WEEKLY": {"price": 599, "duration_days": 7, "sub_service": "SUPER_MATINO_WEEKLY"},
    "MONTHLY": {"price": 1799, "duration_days": 30, "sub_service": "SUPER_MATINO_MONTHLY"},
    "BUY1": {"price": 150, "duration_days": 1, "sub_service": "SUPER_MATINO_BUY1"},
    "BUY2": {"price": 300, "duration_days": 1, "sub_service": "SUPER_MATINO_BUY2"},
    "BUY3": {"price": 750, "duration_days": 1, "sub_service": "SUPER_MATINO_BUY3"},
    "BUY4": {"price": 1500, "duration_days": 1, "sub_service": "SUPER_MATINO_BUY4"},
    "BUY5": {"price": 2250, "duration_days": 1, "sub_service": "SUPER_MATINO_BUY5"},
    "BUY6": {"price": 3750, "duration_days": 1, "sub_service": "SUPER_MATINO_BUY6"}
}

# ====== StaticCode Mapping ======
MPS_CODE_MAP = {
    "0": "Transaction success",
    "100": "Transaction was processed",
    "1": "msisdn not found",
    "4": "IP Client was wrong",
    "11": "missed parameter",
    "13": "missed parameter",
    "14": "cp request id not found",
    "15": "value is not found",
    "16": "aes key is not found",
    "17": "name item is not found",
    "18": "category item is not found",
    "22": "CP code is not valid or not active",
    "23": "Payment is not valid",
    "24": "transaction not confirm before",
    "25": "CP Request Id is not valid",
    "101": "transaction was error",
    "102": "transaction was error when register",
    "103": "got error when pay by mobile account",
    "104": "Error when cancelling service",
    "201": "Signal is not valid",
    "202": "transaction was error or password not valid",
    "207": "Conflict service when register",
    "401": "not enough balance",
    "402": "Subscriber check thanh toan fail",
    "403": "msisdn not existed",
    "404": "msisdn is not valid",
    "405": "msisdn was changed owner",
    "406": "not found mobile",
    "407": "missing parameters",
    "408": "msisdn is using service",
    "409": "msisdn was two ways blocked",
    "410": "msisdn is not valid",
    "411": "msisdn canceled service",
    "412": "msisdn not using service",
    "413": "parameter is not valid",
    "414": "msisdn in period recharge (recharge time < next charge time)",
    "415": "OTP code is not valid",
    "416": "OTP not exist or timeout",
    "417": "Error USSD time out",
    "440": "System error",
    "501": "msisdn not register",
    "203": "MPS account not exist (msisdn/password not valid)",
    "204": "MPS account exist but msisdn not register CP service",
    "205": "MPS account exist and registed CP service",
    "503": "MPS was error",
}

# ====== Helper Functions ======
async def ensure_user_exists(db: AsyncSession, msisdn: str, channel: str = "WEB") -> User:
    """Đảm bảo user tồn tại trong database"""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.msisdn == msisdn))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            msisdn=msisdn,
            display_name=f"user_{msisdn[-4:]}",
            email=None,
            country="MM",
            api_token=secrets.token_hex(32)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


# async def call_mps_charge(msisdn: str, cmd: str, sub_service_name: str, price: int):
#     """
#     Call MPS API with step-by-step logging
#     """
#     try:
#         session_id = str(int(time.time() * 1000))
#         request_id = str(random.randint(10000000000, 99999999999))
        
#         logger.info("=" * 80)
#         logger.info(f"SESS:{session_id}")
#         logger.info(f"REQ:{request_id}")
#         logger.info(f"======> check key at folder :config/key/mytel/{sub_service_name}/")
        
#         # STEP 1: Build raw input data
#         logger.info("==============>>>>> BUILD DATA TO SEND TO MPS<<===============")
        
#         raw_input = (
#             f"CATE=BLANK&SUB={sub_service_name}&ITEM=NULL&SUB_CP=null&"
#             f"SESS={session_id}&PRICE={price}&SOURCE=CLIENT&IMEI=NULL&"
#             f"CONT=null&TYPE=MOBILE&MOBILE={msisdn}&REQ={request_id}"
#         )
        
#         logger.info(f"step 1: data input  -------->{raw_input}")
#         logger.info(f"  → PRICE={price} (from package config)")
        
#         # STEP 2: Encrypt with AES
#         aes_result = encrypt_with_mps_public_key_v2(sub_service_name, raw_input, step=2)
#         logger.info(f"step 2: decode AES for input -------> (encrypted_value shown in step 3)")
        
#         # STEP 3: Encrypt with RSA
#         encrypted_data = aes_result["rsa_encrypted_base64"]
#         logger.info(f"step 3: input add RSA for input --->{encrypted_data[:200]}...")
        
#         # STEP 4: Create signature
#         private_key = load_private_key(sub_service_name)
#         signature_result = sign_data_v2(encrypted_data, private_key)
#         signature = signature_result["signature_base64"]
        
#         signature_urlencoded = quote(signature, safe='')
#         logger.info(f"step 4: create signature for authentication ---> {signature_urlencoded[:200]}...")
        
#         # STEP 5: Build final URL
#         data_urlencoded = quote(encrypted_data, safe='')
        
#         query_string = (
#             f"PRO={MPS_CONFIG['cp_code']}&"
#             f"SER={MPS_CONFIG['service_name']}&"
#             f"SUB={sub_service_name}&"
#             f"CMD={cmd}&"
#             f"DATA={data_urlencoded}&"
#             f"SIG={signature_urlencoded}"
#         )
        
#         full_url = f"{MPS_CONFIG['base_url']}?{query_string}"
#         logger.info(f"step 5: authentication signature ----------> (will be verified by MPS)")
#         logger.info(f"step 6. url send mps: {full_url[:200]}...")
        
#         # STEP 6: Send request to MPS
#         async with httpx.AsyncClient(
#             timeout=MPS_CONFIG["timeout"],
#             follow_redirects=True,
#             http1=True,
#             http2=False,
#             verify=True
#         ) as client:
#             response = await client.get(full_url, headers=MPS_HEADERS)
        
#         logger.info("=" * 80)
#         logger.info(f"======> check key at folder :config/key/mytel/{sub_service_name}/")
#         logger.info("================>>>DECODE DATA RETURN FROM MPS<<===============")
        
#         # STEP 7-10: Process MPS response
#         response_text = response.text.strip()
        
#         logger.info(f"step 7: data receive from mps dataN = -----> {response_text[:200]}")
#         logger.info(f"step 8: check signuature ---------> (skipped for now)")
        
#         if response.status_code == 200 and "|" in response_text:
#             parts = response_text.split("|")
#             mps_code = parts[0]
#             mps_message = parts[1] if len(parts) > 1 else ""
#             transaction_id = parts[2] if len(parts) > 2 else None
#             expire_time = parts[3] if len(parts) > 3 else None
            
#             logger.info(f"step 9: decode data return from mps ----> REQ={request_id}&RES={mps_code}&MOBILE={msisdn}&PRICE={price}&CMD={cmd}&SOURCE=CLIENT&DESC={sub_service_name}")
#             logger.info(f"step 10: analyse RES code return ---> RES={mps_code}==> {mps_message}")
#             logger.info(f"mps response value:{mps_code}|{mps_message}")
            
#             return {
#                 "code": mps_code,
#                 "message": mps_message,
#                 "transaction_id": transaction_id,
#                 "expire_time": expire_time,
#             }
#         else:
#             logger.error(f"Unexpected response: status={response.status_code}, body={response_text[:200]}")
#             return {
#                 "code": str(response.status_code),
#                 "message": response_text[:200],
#                 "transaction_id": None,
#                 "expire_time": None,
#             }
            
#     except Exception as e:
#         logger.error(f"Error calling MPS: {str(e)}", exc_info=True)
#         return {
#             "code": "500",
#             "message": str(e),
#             "transaction_id": None,
#             "expire_time": None,
#         }

async def call_mps_charge(msisdn: str, cmd: str, sub_service_name: str, price: int):
    """
    Call MPS API, handle encryption and decryption (Java EncryptUtil compatible)
    """
    try:
        import time, random, httpx
        from urllib.parse import quote

        session_id = str(int(time.time() * 1000))
        request_id = str(random.randint(10000000000, 99999999999))

        logger.info("=" * 80)
        logger.info(f"➡️ START CALL_MPS_CHARGE: {cmd} | SUB={sub_service_name} | MSISDN={msisdn}")
        logger.info(f"SESSION_ID={session_id} | REQUEST_ID={request_id}")

        # STEP 1: Build input
        raw_input = (
            f"CATE=BLANK&SUB={sub_service_name}&ITEM=NULL&SUB_CP=null&"
            f"SESS={session_id}&PRICE={price}&SOURCE=CLIENT&IMEI=NULL&"
            f"CONT=null&TYPE=MOBILE&MOBILE={msisdn}&REQ={request_id}"
        )
        logger.info(f"🧩 step 1: data input -> {raw_input}")

        # STEP 2-4: Encrypt and sign (handled by existing encrypt_with_mps_public_key_v2)
        aes_result = encrypt_with_mps_public_key_v2(sub_service_name, raw_input, step=2)
        encrypted_data = aes_result["rsa_encrypted_base64"]

        private_key = load_private_key(sub_service_name)
        signature_result = sign_data_v2(encrypted_data, private_key)
        signature = quote(signature_result["signature_base64"], safe='')

        full_url = (
            f"{MPS_CONFIG['base_url']}?PRO={MPS_CONFIG['cp_code']}"
            f"&SER={MPS_CONFIG['service_name']}"
            f"&SUB={sub_service_name}"
            f"&CMD={cmd}"
            f"&DATA={quote(encrypted_data, safe='')}"
            f"&SIG={signature}"
        )

        logger.info(f"🔗 step 6. url send mps: {full_url}")

        # STEP 5: Send request
        async with httpx.AsyncClient(timeout=MPS_CONFIG["timeout"]) as client:
            response = await client.get(full_url, headers=MPS_HEADERS)

        response_text = response.text.strip()
        logger.info(f"📩 step 7: data receive from MPS -> {response_text[:200]}")

        # STEP 6: Decrypt MPS response (may be plain DATA=... or raw base64)
        try:
            decrypted_text = decrypt_with_mps_private_key_v2(sub_service_name, response_text)
        except Exception as e:
            logger.error(f"❌ Failed to decrypt DATA response: {e}", exc_info=True)
            decrypted_text = ""

        # STEP 7: Parse decrypted text
        mps_code = "500"
        mps_message = "Unknown error"
        transaction_id = request_id

        if decrypted_text:
            # Example: REQ=11111111111111&RES=417&MOBILE=9686368706&PRICE=0&CMD=MOBILE...
            pairs = dict(item.split("=") for item in decrypted_text.split("&") if "=" in item)
            mps_code = pairs.get("RES", "500")
            mps_message = MPS_CODE_MAP.get(mps_code, "Unknown error")
            transaction_id = pairs.get("REQ", request_id)

            logger.info(f"✅ step 9: decode RES={mps_code} -> {mps_message}")
        else:
            logger.warning(f"⚠️ step 9: Empty decrypted data, using raw response fallback")

        return {
            "code": mps_code,
            "message": mps_message,
            "transaction_id": transaction_id,
            "raw": decrypted_text or response_text,
        }

    except Exception as e:
        logger.error(f"❌ Error in call_mps_charge: {str(e)}", exc_info=True)
        return {
            "code": "500",
            "message": str(e),
            "transaction_id": None,
            "raw": None,
        }
        
def map_mps_status(mps_code: str) -> str:
    """
    Map MPS result code -> internal system status
    - 0: success
    - 416, 417: timeout or user cancel
    - others: failed
    """
    if mps_code == "0":
        return "success"
    elif mps_code in ["416", "417"]:
        return "timeout" if mps_code == "417" else "user_cancel"
    else:
        return "failed"

async def update_customer_record(
    db: AsyncSession,
    msisdn: str,
    package_name: str,
    cmd: str,
    mps_result: dict,
    channel: str
) -> None:
    """Update database after charge - Updated for new schema"""
    from sqlalchemy import select
    
    try:
        now = datetime.now(MYANMAR_TZ)
        package_info = PACKAGE_CONFIG.get(package_name, {})
        await ensure_user_exists(db, msisdn, channel)
        status = map_mps_status(mps_result["code"])
        
        # ✅ REGISTER SUCCESS
        if cmd == "REGISTER" and status == "success":
            expire_dt = now + timedelta(days=package_info.get("duration_days", 1))
            
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing customer
                existing.status = 'active'
                existing.current_charged_date = now
                existing.next_charge_date = expire_dt
                existing.channel = channel
                existing.last_update = now
                existing.note = "Web charge - Registration updated"
            else:
                # Create new customer
                new_customer = MyIDCustomer(
                    msisdn=msisdn,
                    info="DK",
                    create_date=now,
                    last_update=now,
                    channel=channel,
                    status='active',
                    current_charged_date=now,
                    next_charge_date=expire_dt,
                    package_name=package_name,
                    price=package_info.get("price", 0),
                    note="Web charge - New registration"
                )
                db.add(new_customer)
            
            # Log charging
            log_entry = MyIDLogCharging(
                action='register',
                msisdn=msisdn,
                package_code=package_name,
                reg_datetime=now,
                sta_datetime=now,
                end_datetime=expire_dt,
                expire_datetime=expire_dt,
                channel=channel,
                charge_price=package_info.get("price", 0),
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                mode="REAL",
                is_success=0  # 0 = success in new schema
            )
            db.add(log_entry)
            
            # History
            history = MyIDCustomerHistory(
                msisdn=msisdn,
                info="DK",
                create_date=now,
                last_update=now,
                channel=channel,
                current_charged_date=now,
                next_charge_date=expire_dt,
                package_name=package_name,
                price=package_info.get("price", 0),
                note="Web charge - Registration successful",
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                action='register',
                result=0  # 0 = success
            )
            db.add(history)
            
        elif cmd == "CHARGE" and status == "success":
            expire_dt = now + timedelta(days=package_info.get("duration_days", 1))

            # Cập nhật hoặc tạo mới MyIDCustomer
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.current_charged_date = now
                existing.next_charge_date = expire_dt
                existing.last_update = now
                existing.note = "Web charge - Renewal success"
            else:
                new_customer = MyIDCustomer(
                    msisdn=msisdn,
                    info="CHARGE",
                    create_date=now,
                    last_update=now,
                    channel=channel,
                    status='active',
                    current_charged_date=now,
                    next_charge_date=expire_dt,
                    package_name=package_name,
                    price=package_info.get("price", 0),
                    note="Web charge - New charge"
                )
                db.add(new_customer)

            # Log charging
            log_entry = MyIDLogCharging(
                action='one_time',
                msisdn=msisdn,
                package_code=package_name,
                reg_datetime=now,
                sta_datetime=now,
                end_datetime=expire_dt,
                expire_datetime=expire_dt,
                channel=channel,
                charge_price=package_info.get("price", 0),
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                mode="REAL",
                is_success=0  # 0 = success
            )
            db.add(log_entry)

            # History
            history = MyIDCustomerHistory(
                msisdn=msisdn,
                info="CHARGE",
                create_date=now,
                last_update=now,
                channel=channel,
                current_charged_date=now,
                next_charge_date=expire_dt,
                package_name=package_name,
                price=package_info.get("price", 0),
                note="Web charge - Charge successful",
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                action='one_time',
                result=0
            )
            db.add(history)
            
        # ✅ CANCEL SUCCESS
        elif cmd == "CANCEL" and status == "success":
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                # Move to cancel table
                cancel_record = MyIDCustomerCancel(
                    msisdn=customer.msisdn,
                    info="HUY",
                    create_date=customer.create_date,
                    last_update=now,
                    channel=channel,
                    status=0,  # 0 = success
                    current_charged_date=customer.current_charged_date,
                    next_charge_date=customer.next_charge_date,
                    package_name=package_name,
                    last_unreg=now,
                    note="Web charge - Cancelled",
                    cancel_date=now,
                    cancel_reason="Web cancellation",
                    transaction_id=mps_result.get("transaction_id")
                )
                db.add(cancel_record)
                
                # Delete from active customers
                await db.delete(customer)
            
            # Log charging
            log_entry = MyIDLogCharging(
                action='cancel',
                msisdn=msisdn,
                package_code=package_name,
                reg_datetime=now,
                channel=channel,
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                mode="REAL",
                is_success=0  # 0 = success
            )
            db.add(log_entry)
            
            # History
            history = MyIDCustomerHistory(
                msisdn=msisdn,
                info="HUY",
                create_date=now,
                last_update=now,
                channel=channel,
                package_name=package_name,
                note="Web charge - Cancellation successful",
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                action='cancel',
                result=0  # 0 = success
            )
            db.add(history)
        
        # ✅ FAILED REQUESTS
        if status != "success":
            # History for failed request
            history = MyIDCustomerHistory(
                msisdn=msisdn,
                info=cmd,
                create_date=now,
                last_update=now,
                channel=channel,
                package_name=package_name,
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                action='register' if cmd == "REGISTER" else 'cancel',
                result=1,  # 1 = failed
                note=f"Web charge failed - {mps_result.get('message', 'Unknown error')}"
            )
            db.add(history)
            
            # Log charging failed
            log_entry = MyIDLogCharging(
                action='register' if cmd == "REGISTER" else 'cancel',
                msisdn=msisdn,
                package_code=package_name,
                reg_datetime=now,
                channel=channel,
                charge_price=package_info.get("price", 0) if cmd == "REGISTER" else None,
                transaction_id=mps_result.get("transaction_id"),
                mps_command=cmd,
                mode="REAL",
                is_success=1  # 1 = failed
            )
            db.add(log_entry)
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error updating customer record: {str(e)}")
        await db.rollback()
        raise

# ====== API Endpoints ======
@router.post("/web/charge", response_model=WebChargeResponse)
async def web_charge(
    request: WebChargeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Web charge endpoint - Updated for new models/schemas
    """
    try:
        logger.info(f"Web charge request: {request.dict()}")
        
        if request.package_name not in PACKAGE_CONFIG:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid package: {request.package_name}"
            )
        
        package_info = PACKAGE_CONFIG[request.package_name]
        sub_service = request.sub_service_name or package_info["sub_service"]
        
        # Call MPS API
        mps_result = await call_mps_charge(
            msisdn=request.msisdn,
            cmd=request.cmd,
            sub_service_name=sub_service,
            price=package_info["price"]
        )
        
        # Map status
        internal_status = map_mps_status(mps_result["code"])
        
        # Update database
        await update_customer_record(
            db=db,
            msisdn=request.msisdn,
            package_name=request.package_name,
            cmd=request.cmd,
            mps_result=mps_result,
            channel=request.channel
        )
        
        # Calculate expire datetime
        expire_dt = None
        if internal_status == "success":
            now = datetime.now(MYANMAR_TZ)
            expire_dt = now + timedelta(days=package_info["duration_days"])
        
        # Build response
        response = WebChargeResponse(
            status=internal_status,
            message=get_user_message(request.cmd, internal_status),
            mps_code=mps_result["code"],
            mps_message=mps_result["message"],
            transaction_id=mps_result.get("transaction_id"),
            expire_datetime=expire_dt,
            charge_price=package_info["price"] if internal_status == "success" else None,
            data={
                "package_name": request.package_name,
                "msisdn": request.msisdn,
                "channel": request.channel
            }
        )
        
        logger.info(f"Web charge response: {response.dict()}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in web_charge: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def get_user_message(cmd: str, status: str) -> str:
    """Generate user-friendly message"""
    messages = {
        ("REGISTER", "success"): "Đăng ký gói thành công!",
        ("REGISTER", "failed"): "Đăng ký thất bại. Vui lòng thử lại.",
        ("REGISTER", "user_cancel"): "Bạn đã hủy đăng ký.",
        ("REGISTER", "timeout"): "Yêu cầu hết thời gian. Vui lòng thử lại.",
        ("CANCEL", "success"): "Hủy gói thành công!",
        ("CANCEL", "failed"): "Hủy gói thất bại. Vui lòng thử lại.",
        ("CHARGE", "success"): "Gia hạn gói thành công!",
        ("CHARGE", "failed"): "Gia hạn thất bại. Vui lòng kiểm tra tài khoản.",
    }
    return messages.get((cmd, status), "Xử lý yêu cầu thất bại.")

@router.get("/web/check-subscription")
async def check_subscription(
    msisdn: str = Query(..., description="Số điện thoại"),
    db: AsyncSession = Depends(get_db)
):
    """Check user subscription status - Updated for new schema"""
    from sqlalchemy import select
    
    try:
        stmt = select(MyIDCustomer).where(
            MyIDCustomer.msisdn == msisdn,
            MyIDCustomer.status == 'active'
        )
        result = await db.execute(stmt)
        subscriptions = result.scalars().all()
        
        return {
            "msisdn": msisdn,
            "has_subscription": len(subscriptions) > 0,
            "subscriptions": [
                {
                    "package_name": sub.package_name,
                    "status": sub.status,
                    "expire_date": sub.next_charge_date.isoformat() if sub.next_charge_date else None,
                    "price": sub.price,
                    "channel": sub.channel
                }
                for sub in subscriptions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error checking subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))