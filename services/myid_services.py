# services/myid_services.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import secrets
import string
import logging
import os

from models.myid_models import MyIDCustomer, MyIDCustomerHistory, MyIDCustomerCancel, MyIDLogCharging
from schemas.myid_schemas import SubRequest, ResultRequest, ContentRequest, ChargingAction

load_dotenv()
logger = logging.getLogger(__name__)

class MPSAuthService:
    """Service để xác thực requests từ MPS"""
    
    def __init__(self):
        self.expected_username = os.getenv("MPS_API_USERNAME", "super_matino_api_2025")
        self.expected_password = os.getenv("MPS_API_PASSWORD", "SMat!n0_S3cur3_K3y_2025@MPS")
    
    def validate_mps_credentials(self, request_data: Dict[str, Any]) -> bool:
        """Validate MPS authentication credentials"""
        try:
            username = request_data.get("username", "")
            password = request_data.get("password", "")
            
            if not username or not password:
                logger.warning("Missing username or password in MPS request")
                return False
            
            if username != self.expected_username:
                logger.warning(f"Invalid username from MPS: {username}")
                return False
                
            if password != self.expected_password:
                logger.warning("Invalid password from MPS")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating MPS credentials: {str(e)}")
            return False

class MyIDService:
    
    @staticmethod
    def parse_charge_time(chargetime: str) -> datetime:
        """Parse chargetime từ MPS format YYYYMMDDHHMISS"""
        try:
            if len(chargetime) == 14:
                return datetime.strptime(chargetime, "%Y%m%d%H%M%S")
            elif len(chargetime) == 12:
                return datetime.strptime(chargetime + "00", "%Y%m%d%H%M%S")
            else:
                return datetime.now()
        except ValueError:
            logger.error(f"Invalid chargetime format: {chargetime}")
            return datetime.now()
    
    @staticmethod
    def get_package_name_from_service_id(service_id: str) -> str:
        """Map từ service_id sang package code nội bộ"""
        service_upper = service_id.upper()
        if "DAILY" in service_upper:
            return "DAILY"
        elif "WEEKLY" in service_upper:
            return "WEEKLY"
        elif "MONTHLY" in service_upper:
            return "MONTHLY"
        elif "BUY" in service_upper:
            return service_id
        elif "OTP" in service_upper:
            return "OTP"
        return service_id
    
    @staticmethod
    def calculate_next_charge_date(package_name: str, current_date: datetime) -> datetime:
        """Tính ngày charge tiếp theo dựa trên package"""
        if package_name == "DAILY":
            return current_date + timedelta(days=1)
        elif package_name == "WEEKLY":
            return current_date + timedelta(weeks=1)
        elif package_name == "MONTHLY":
            return current_date + timedelta(days=30)
        else:
            return current_date + timedelta(days=1)
    
    @staticmethod
    def get_channel_from_command(command: str) -> str:
        """Determine channel from MPS command"""
        cmd = (command or "").strip().upper()
        
        if cmd in ["YES", "OFF"]:
            return "SMS"
        elif cmd in ["1", "0"]:
            return "USSD"
        elif cmd == "MONFEE":
            return "CP"
        else:
            return "UNKNOWN"
    
    async def check_idempotency(self, db: AsyncSession, transaction_id: str) -> bool:
        """
        Check if transaction has been processed before
        Returns True if already processed, False otherwise
        """
        if not transaction_id:
            return False
            
        stmt = select(MyIDLogCharging).where(
            MyIDLogCharging.transaction_id == transaction_id
        )
        result = await db.execute(stmt)
        existing_log = result.scalar_one_or_none()
        
        return existing_log is not None
    
    # ✅ HÀM TRUNG TÂM: Ghi log charging với action
    async def log_charging(
        self, db: AsyncSession,
        action: str,  # ✅ THÊM action
        msisdn: str, 
        package_code: str,
        charge_time: datetime, 
        channel: str,
        charge_price: int,
        transaction_id: str,
        mps_command: str,
        mode: str,
        is_success: int  # ✅ 0=success, 1=failed (ĐÃ ĐỔI NGƯỢC)
    ) -> None:
        """Ghi log charging - KHÔNG commit ở đây"""
        try:
            log_entry = MyIDLogCharging(
                action=action,  # ✅ THÊM action vào log
                msisdn=msisdn,
                package_code=package_code,
                reg_datetime=charge_time,
                channel=channel,
                charge_price=charge_price,
                transaction_id=transaction_id,
                mps_command=mps_command,
                mode=mode,
                is_success=is_success  # ✅ 0=success, 1=failed
            )
            db.add(log_entry)
            logger.info(f"Log charging prepared: action={action}, txn={transaction_id}, is_success={is_success} (0=success,1=failed)")
            
        except Exception as e:
            logger.exception(f"Error creating log_charging: {e}")
            raise
    
    # ✅ LOẠI BỎ log_charging_failure riêng - dùng chung log_charging với is_success=0
    
    async def process_sub_request(self, db: AsyncSession, request: SubRequest) -> dict:
        """
        ✅ Xử lý subRequest từ MPS - CẬP NHẬT ĐẦY ĐỦ
        - Xác định action rõ ràng (register/cancel)
        - Luôn ghi log với action
        - Luôn ghi history với action và result
        - Cập nhật status khách hàng
        """
        msisdn = request.msisdn
        txn_id = request.transactionid
        charge_time = self.parse_charge_time(request.chargetime)
        package_name = self.get_package_name_from_service_id(request.serviceid)
        channel = self.get_channel_from_command(request.command)
        price = int(request.amount) if request.amount.isdigit() else 0
        
        # ✅ Xác định action
        action = "register" if request.params == "0" else "cancel"
        
        # Idempotency check
        if txn_id and await self.check_idempotency(db, txn_id):
            logger.info(f"Duplicate transaction: txn={txn_id}, action={action}")
            return {"return_code": "0"}
        
        try:
            # ✅ Xử lý theo action
            if action == "register":
                await self.handle_registration(
                    db, request, charge_time, package_name, channel, price, txn_id
                )
            elif action == "cancel":
                await self.handle_cancellation(
                    db, request, charge_time, package_name, channel, txn_id
                )
            
            # ✅ Ghi log thành công (0=success)
            await self.log_charging(
                db=db,
                action=action,
                msisdn=msisdn,
                package_code=package_name,
                charge_time=charge_time,
                channel=channel,
                charge_price=price,
                transaction_id=txn_id,
                mps_command=request.command,
                mode=request.mode,
                is_success=0  # ✅ 0=success
            )
            
            # COMMIT tất cả
            await db.commit()
            logger.info(f"✅ SubRequest success: action={action}, txn={txn_id}")
            return {"return_code": "0"}
            
        except IntegrityError as e:
            logger.error(f"IntegrityError in subRequest: {str(e)}")
            await db.rollback()
            
            # Duplicate transaction - return success
            if "uq_myid_log_txn" in str(e).lower():
                logger.info(f"Duplicate caught by DB: {txn_id}")
                return {"return_code": "0"}
            
            # Ghi log thất bại trong transaction mới
            try:
                await self.log_charging(
                    db=db, action=action, msisdn=msisdn,
                    package_code=package_name, charge_time=charge_time,
                    channel=channel, charge_price=price,
                    transaction_id=txn_id, mps_command=request.command,
                    mode="ERROR", is_success=1  # ✅ 1=failed
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to log failure")
            
            return {"return_code": "1"}
            
        except Exception as e:
            logger.exception(f"Error in subRequest: {e}")
            await db.rollback()
            
            # Ghi log thất bại
            try:
                await self.log_charging(
                    db=db, action=action, msisdn=msisdn,
                    package_code=package_name, charge_time=charge_time,
                    channel=channel, charge_price=price,
                    transaction_id=txn_id, mps_command=request.command,
                    mode="ERROR", is_success=1  # ✅ 1=failed
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to log failure")
            
            return {"return_code": "1"}
    
    async def process_result_request(self, db: AsyncSession, request: ResultRequest) -> dict:
        """
        ✅ Xử lý resultRequest (gia hạn) - CẬP NHẬT ĐẦY ĐỦ
        """
        msisdn = request.msisdn
        txn_id = request.transactionid
        charge_time = self.parse_charge_time(request.chargetime)
        package_name = self.get_package_name_from_service_id(request.serviceid)
        channel = "CP"
        price = int(request.amount) if request.amount.isdigit() else 0
        
        # ✅ Action luôn là renew
        action = "renew"
        
        # Idempotency check
        if txn_id and await self.check_idempotency(db, txn_id):
            logger.info(f"Duplicate renewal: txn={txn_id}")
            return {"return_code": "0"}
        
        try:
            # Xử lý theo kết quả
            if request.params == "0":  # SUCCESS
                await self.handle_renewal_success(
                    db, request, charge_time, package_name, price, txn_id
                )
                is_success = 0  # ✅ 0=success
            else:  # FAILED
                await self.handle_renewal_failed(
                    db, request, charge_time, package_name, txn_id
                )
                is_success = 1  # ✅ 1=failed
            
            # ✅ Ghi log với action=renew
            await self.log_charging(
                db=db,
                action=action,
                msisdn=msisdn,
                package_code=package_name,
                charge_time=charge_time,
                channel=channel,
                charge_price=price if is_success == 0 else 0,  # ✅ Chỉ ghi giá nếu success
                transaction_id=txn_id,
                mps_command=request.command,
                mode=request.mode,
                is_success=is_success
            )
            
            # COMMIT
            await db.commit()
            logger.info(f"✅ ResultRequest success: action={action}, txn={txn_id}, success={is_success}")
            return {"return_code": "0"}
            
        except IntegrityError as e:
            logger.error(f"IntegrityError in resultRequest: {str(e)}")
            await db.rollback()
            
            if "uq_myid_log_txn" in str(e).lower():
                return {"return_code": "0"}
            
            # Ghi log thất bại
            try:
                await self.log_charging(
                    db=db, action=action, msisdn=msisdn,
                    package_code=package_name, charge_time=charge_time,
                    channel=channel, charge_price=0,
                    transaction_id=txn_id, mps_command=request.command,
                    mode="ERROR", is_success=0
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to log failure")
            
            return {"return_code": "1"}
            
        except Exception as e:
            logger.exception(f"Error in resultRequest: {e}")
            await db.rollback()
            
            # Ghi log thất bại
            try:
                await self.log_charging(
                    db=db, action=action, msisdn=msisdn,
                    package_code=package_name, charge_time=charge_time,
                    channel=channel, charge_price=0,
                    transaction_id=txn_id, mps_command=request.command,
                    mode="ERROR", is_success=0
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to log failure")
            
            return {"return_code": "1"}
    
    async def process_content_request(self, db: AsyncSession, request: ContentRequest) -> dict:
        """
        ✅ Xử lý contentRequest (one-time) - CẬP NHẬT ĐẦY ĐỦ
        """
        msisdn = request.msisdn
        txn_id = request.transactionid
        charge_time = self.parse_charge_time(request.chargetime)
        package_name = "OTP"
        channel = "SMS"
        price = int(request.amount) if request.amount.isdigit() else 0
        
        # ✅ Action luôn là one_time
        action = "one_time"
        
        # Idempotency check
        if txn_id and await self.check_idempotency(db, txn_id):
            logger.info(f"Duplicate content purchase: txn={txn_id}")
            return {"return_code": "0"}
        
        try:
            # ✅ Thêm vào history với action=one_time
            history = MyIDCustomerHistory(
                msisdn=msisdn,
                info="OTP",
                create_date=charge_time,
                channel=channel,
                current_charged_date=charge_time,
                package_name=package_name,
                price=price,
                note="One-time package purchase",
                transaction_id=txn_id,
                mps_command=request.params,
                action=action,  # ✅ THÊM action
                result=0  # ✅ 0=success
            )
            db.add(history)
            
            # ✅ Ghi log với action=one_time
            await self.log_charging(
                db=db,
                action=action,
                msisdn=msisdn,
                package_code=package_name,
                charge_time=charge_time,
                channel=channel,
                charge_price=price,
                transaction_id=txn_id,
                mps_command=request.params,
                mode=request.mode,
                is_success=1
            )
            
            # COMMIT
            await db.commit()
            logger.info(f"✅ ContentRequest success: action={action}, txn={txn_id}")
            return {"return_code": "0"}
            
        except IntegrityError as e:
            logger.error(f"IntegrityError in contentRequest: {str(e)}")
            await db.rollback()
            
            if "uq_myid_log_txn" in str(e).lower():
                return {"return_code": "0"}
            
            # Ghi log thất bại
            try:
                await self.log_charging(
                    db=db, action=action, msisdn=msisdn,
                    package_code=package_name, charge_time=charge_time,
                    channel=channel, charge_price=0,
                    transaction_id=txn_id, mps_command=request.params,
                    mode="ERROR", is_success=0
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to log failure")
            
            return {"return_code": "1"}
            
        except Exception as e:
            logger.exception(f"Error in contentRequest: {e}")
            await db.rollback()
            
            # Ghi log thất bại
            try:
                await self.log_charging(
                    db=db, action=action, msisdn=msisdn,
                    package_code=package_name, charge_time=charge_time,
                    channel=channel, charge_price=0,
                    transaction_id=txn_id, mps_command=request.params,
                    mode="ERROR", is_success=0
                )
                await db.commit()
            except Exception:
                logger.exception("Failed to log failure")
            
            return {"return_code": "1"}
    
    # ===================================================================
    # ✅ CÁC HÀM HANDLER - CẬP NHẬT ĐẦY ĐỦ
    # ===================================================================
    
    async def handle_registration(
        self, db: AsyncSession, request: SubRequest, 
        charge_time: datetime, package_name: str,
        channel: str, price: int, txn_id: str
    ) -> None:
        """
        ✅ Xử lý đăng ký - CẬP NHẬT
        - Cập nhật status='active'
        - Thêm vào history với action='register', result=0
        """
        try:
            next_charge_date = self.calculate_next_charge_date(package_name, charge_time)
            
            # Check existing customer
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == request.msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                # Update existing - ✅ SET status='active'
                customer.info = package_name
                customer.last_update = charge_time
                customer.channel = channel
                customer.status = 'active'  # ✅ ACTIVE
                customer.current_charged_date = charge_time
                customer.next_charge_date = next_charge_date
                customer.price = price
                customer.note = "Subscription renewed"
            else:
                # Create new - ✅ SET status='active'
                customer = MyIDCustomer(
                    msisdn=request.msisdn,
                    info=package_name,
                    create_date=charge_time,
                    channel=channel,
                    status='active',  # ✅ ACTIVE
                    current_charged_date=charge_time,
                    next_charge_date=next_charge_date,
                    package_name=package_name,
                    price=price,
                    note="New subscription"
                )
                db.add(customer)
            
            # ✅ Thêm vào history với action='register', result=0
            history = MyIDCustomerHistory(
                msisdn=request.msisdn,
                info=package_name,
                create_date=charge_time,
                channel=channel,
                current_charged_date=charge_time,
                next_charge_date=next_charge_date,
                package_name=package_name,
                price=price,
                note="Registration successful",
                transaction_id=txn_id,
                mps_command=request.command,
                action="register",  # ✅ ACTION
                result=0  # ✅ 0=success
            )
            db.add(history)
            
        except Exception as e:
            logger.exception("Error in handle_registration")
            raise
    
    async def handle_cancellation(
        self, db: AsyncSession, request: SubRequest,
        charge_time: datetime, package_name: str,
        channel: str, txn_id: str
    ) -> None:
        """
        ✅ Xử lý hủy - CẬP NHẬT
        - Cập nhật status='cancelled'
        - Lưu vào bảng myid_customer_cancel
        - Thêm vào history với action='cancel', result=0
        """
        try:
            # Find existing customer
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == request.msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                # ✅ Lưu vào bảng cancel
                cancel_record = MyIDCustomerCancel(
                    msisdn=customer.msisdn,
                    info=f"HUY",
                    create_date=customer.create_date,
                    channel=channel,
                    status=0,  # 0=success
                    current_charged_date=customer.current_charged_date,
                    next_charge_date=customer.next_charge_date,
                    package_name=package_name,
                    last_unreg=charge_time,
                    note="Subscription cancelled",
                    cancel_date=charge_time,
                    cancel_reason="User request",
                    transaction_id=txn_id
                )
                db.add(cancel_record)
                
                # ✅ Cập nhật status='cancelled' trước khi xóa
                customer.status = 'cancelled'
                
                # Xóa khỏi active customers
                await db.delete(customer)
            
            # ✅ Thêm vào history với action='cancel', result=0
            history = MyIDCustomerHistory(
                msisdn=request.msisdn,
                info="HUY",
                create_date=charge_time,
                channel=channel,
                package_name=package_name,
                note="Cancellation successful",
                transaction_id=txn_id,
                mps_command=request.command,
                action="cancel",  # ✅ ACTION
                result=0  # ✅ 0=success
            )
            db.add(history)
            
        except Exception as e:
            logger.exception("Error in handle_cancellation")
            raise
    
    async def handle_renewal_success(
        self, db: AsyncSession, request: ResultRequest,
        charge_time: datetime, package_name: str,
        price: int, txn_id: str
    ) -> None:
        """
        ✅ Xử lý gia hạn thành công - CẬP NHẬT
        - Cập nhật status='active'
        - Thêm vào history với action='renew', result=0
        """
        try:
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == request.msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            customer = result.scalar_one_or_none()
            
            next_charge_date = self.calculate_next_charge_date(package_name, charge_time)
            
            if customer:
                # ✅ Cập nhật status='active'
                customer.current_charged_date = charge_time
                customer.next_charge_date = next_charge_date
                customer.last_update = charge_time
                customer.status = 'active'  # ✅ ACTIVE
                customer.note = "Renewal successful"
            else:
                # Tạo mới nếu chưa có
                customer = MyIDCustomer(
                    msisdn=request.msisdn,
                    info=package_name,
                    create_date=charge_time,
                    channel="CP",
                    status='active',  # ✅ ACTIVE
                    current_charged_date=charge_time,
                    next_charge_date=next_charge_date,
                    package_name=package_name,
                    price=price,
                    note="Renewal successful"
                )
                db.add(customer)
            
            # ✅ Thêm vào history với action='renew', result=0
            history = MyIDCustomerHistory(
                msisdn=request.msisdn,
                info=package_name,
                create_date=charge_time,
                channel="CP",
                current_charged_date=charge_time,
                next_charge_date=next_charge_date,
                package_name=package_name,
                price=price,
                note="Renewal successful",
                transaction_id=txn_id,
                mps_command=request.command,
                action="renew",  # ✅ ACTION
                result=0  # ✅ 0=success
            )
            db.add(history)
            
        except Exception as e:
            logger.exception("Error in handle_renewal_success")
            raise
    
    async def handle_renewal_failed(
        self, db: AsyncSession, request: ResultRequest,
        charge_time: datetime, package_name: str, txn_id: str
    ) -> None:
        """
        ✅ Xử lý gia hạn thất bại - CẬP NHẬT
        - Cập nhật status='inactive'
        - Thêm vào history với action='renew', result=1
        """
        try:
            # ✅ Thêm vào history với action='renew', result=1 (failed)
            history = MyIDCustomerHistory(
                msisdn=request.msisdn,
                info=package_name,
                create_date=charge_time,
                channel="CP",
                package_name=package_name,
                note="Renewal failed",
                transaction_id=txn_id,
                mps_command=request.command,
                action="renew",  # ✅ ACTION
                result=1  # ✅ 1=failed
            )
            db.add(history)
            
            # ✅ Cập nhật customer status='inactive'
            stmt = select(MyIDCustomer).where(
                MyIDCustomer.msisdn == request.msisdn,
                MyIDCustomer.package_name == package_name
            )
            result = await db.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if customer:
                customer.last_update = charge_time
                customer.status = 'inactive'  # ✅ INACTIVE
                customer.note = "Renewal failed"
            
        except Exception as e:
            logger.exception("Error in handle_renewal_failed")
            raise
    
    # ===================================================================
    # INTERNAL API METHODS (không thay đổi)
    # ===================================================================
    
    async def get_customers(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[MyIDCustomer]:
        """Get list of active customers"""
        stmt = select(MyIDCustomer).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_customer_by_msisdn(
        self, db: AsyncSession, msisdn: str, 
        package_name: str = None
    ) -> Optional[MyIDCustomer]:
        """Get customer by phone number"""
        stmt = select(MyIDCustomer).where(MyIDCustomer.msisdn == msisdn)
        if package_name:
            stmt = stmt.where(MyIDCustomer.package_name == package_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_charging_logs(
        self, db: AsyncSession, msisdn: str = None,
        skip: int = 0, limit: int = 100
    ) -> List[MyIDLogCharging]:
        """Get charging logs"""
        stmt = select(MyIDLogCharging)
        if msisdn:
            stmt = stmt.where(MyIDLogCharging.msisdn == msisdn)
        stmt = stmt.order_by(MyIDLogCharging.reg_datetime.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()