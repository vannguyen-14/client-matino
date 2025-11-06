# services/mytel_bonus_service.py
import hmac
import hashlib
import json
import httpx
import logging
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from config.mytel_bonus_config import MytelBonusConfig

logger = logging.getLogger(__name__)

class MytelBonusService:
    """Service to interact with Mytel VAS Partner Gateway"""
    
    def __init__(self):
        self.config = MytelBonusConfig()
        self.base_url = self.config.get_base_url()
        self.username = self.config.USERNAME
        self.password = self.config.PASSWORD
        self.secret_key = self.config.SECRET_KEY
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.backoff_multiplier = 2.0
    
    def generate_signature(self, body_data: dict) -> str:
        """
        Generate HMAC-SHA256 signature for request body
        
        Args:
            body_data: Dictionary containing request body
            
        Returns:
            Hex string of HMAC-SHA256 signature
        """
        try:
            # Convert body to JSON string (compact, no spaces)
            json_str = json.dumps(body_data, separators=(',', ':'), ensure_ascii=False)
            
            # Create HMAC-SHA256
            signature = hmac.new(
                key=self.secret_key.encode('utf-8'),
                msg=json_str.encode('utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest().upper()
            
            logger.debug(f"Generated signature for body: {json_str}")
            logger.debug(f"Signature: {signature}")
            
            return signature
            
        except Exception as e:
            logger.error(f"Error generating signature: {str(e)}")
            raise
    
    def generate_ref_trans_id(self, user_id: int, reward_type: str = "LOYALTY") -> str:
        """
        Generate unique refTransId for transaction
        
        Args:
            user_id: User ID
            reward_type: Type of reward (LOYALTY, DATA, etc)
            
        Returns:
            Unique transaction ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{reward_type}_{user_id}_{timestamp}_{unique_id}"
    
    def _normalize_error_message(self, result: Dict[str, Any]) -> str:
        """
        Normalize error messages from Mytel API response
        
        Args:
            result: API response dictionary
            
        Returns:
            Combined error message
        """
        messages = []
        
        # Get top-level message
        if result.get("message"):
            messages.append(result["message"])
        
        # Get result-level error message (if result is dict)
        result_data = result.get("result")
        if isinstance(result_data, dict) and result_data.get("errMessage"):
            messages.append(f"Detail: {result_data['errMessage']}")
        elif isinstance(result_data, str):
            messages.append(f"Detail: {result_data}")
        
        return " | ".join(messages) if messages else "Unknown error"
    
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry
        
        Args:
            method: HTTP method (GET, POST, etc)
            url: Request URL
            **kwargs: Additional arguments for httpx request
            
        Returns:
            Response object
            
        Raises:
            Exception after all retries exhausted
        """
        last_exception = None
        delay = self.retry_delay
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, **kwargs)
                    elif method.upper() == "POST":
                        response = await client.post(url, **kwargs)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    # Raise for 5xx errors to trigger retry
                    if 500 <= response.status_code < 600:
                        raise httpx.HTTPStatusError(
                            f"Server error: {response.status_code}",
                            request=response.request,
                            response=response
                        )
                    
                    return response
                    
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.backoff_multiplier
                else:
                    logger.error(
                        f"Request failed after {self.max_retries} attempts: {str(e)}"
                    )
            except Exception as e:
                # Don't retry for other exceptions
                logger.error(f"Non-retryable error: {str(e)}")
                raise
        
        raise last_exception
    
    async def add_loyalty_points(
        self,
        msisdn: str,
        points: int,
        ref_trans_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add loyalty points to user's account
        
        Args:
            msisdn: User phone number (e.g., "959662762610")
            points: Number of loyalty points to add
            ref_trans_id: Optional custom reference transaction ID
            user_id: Optional user ID for auto-generating ref_trans_id
            
        Returns:
            Dictionary containing response from Mytel API
        """
        try:
            # Validate and get package code
            package_code = self.config.get_package_code(points)
            
            # Generate ref_trans_id if not provided
            if not ref_trans_id:
                if user_id is None:
                    ref_trans_id = str(uuid.uuid4())
                else:
                    ref_trans_id = self.generate_ref_trans_id(user_id, "LOYALTY")
            
            # Prepare request body
            body = {
                "msisdn": msisdn,
                "packageCode": package_code,
                "refTrans": ref_trans_id
            }
            
            # Generate signature
            signature = self.generate_signature(body)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "signature": signature
            }
            
            # API URL
            url = f"{self.base_url}{self.config.API_ADD_PRIZE}"
            
            # ========== ENHANCED LOGGING ==========
            logger.info("="*80)
            logger.info("📤 SENDING REQUEST TO MYTEL API")
            logger.info("="*80)
            logger.info(f"🔗 URL: {url}")
            logger.info(f"🔐 Auth Username: {self.username}")
            logger.info(f"🔐 Auth Password: {'*' * len(self.password)}")
            logger.info(f"📋 Request Body:")
            logger.info(f"   - msisdn: {msisdn}")
            logger.info(f"   - packageCode: {package_code}")
            logger.info(f"   - refTrans: {ref_trans_id}")
            logger.info(f"   - points (context): {points}")
            logger.info(f"🔑 Headers:")
            logger.info(f"   - Content-Type: {headers['Content-Type']}")
            logger.info(f"   - signature: {signature}")
            logger.info(f"📦 Full Request Body JSON: {json.dumps(body, indent=2)}")
            logger.info(f"🔏 Signature generated from: {json.dumps(body, separators=(',', ':'), ensure_ascii=False)}")
            logger.info("="*80)
            
            json_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False)
            
            # Make request with retry
            response = await self._make_request_with_retry(
                method="POST",
                url=url,
                content=json_str.encode("utf-8"),   # 👈 gửi raw bytes
                headers=headers,
                auth=(self.username, self.password)
            )
            
            # ========== RESPONSE LOGGING ==========
            logger.info("="*80)
            logger.info("📥 RECEIVED RESPONSE FROM MYTEL API")
            logger.info("="*80)
            logger.info(f"📊 Status Code: {response.status_code}")
            logger.info(f"📋 Response Headers: {dict(response.headers)}")
            logger.info(f"📦 Response Body: {response.text}")
            logger.info("="*80)
            
            # Parse response
            result = response.json()
            
            logger.info(f"✅ Parsed Response JSON: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Enhanced validation: check both success flag and status
            # Handle case where result["result"] can be string or dict
            is_successful = False
            if result.get("success"):
                result_data = result.get("result")
                if isinstance(result_data, dict):
                    is_successful = result_data.get("status") == "SUCCESS"
            
            # Add normalized error message
            if not is_successful:
                result["error_message"] = self._normalize_error_message(result)
            
            if is_successful:
                logger.info(
                    f"✅ Successfully added {points} loyalty points to {msisdn}. "
                    f"TransId: {result['result']['id']}, "
                    f"RefLoyaltyId: {result['result'].get('refLoyaltyId')}"
                )
            else:
                logger.error(
                    f"❌ Failed to add loyalty points to {msisdn}. "
                    f"Code: {result.get('code')}, "
                    f"Status: {result.get('result', {}).get('status') if isinstance(result.get('result'), dict) else 'N/A'}, "
                    f"Error: {result.get('error_message')}"
                )
            
            return result
            
        except ValueError as e:
            logger.error(f"Invalid loyalty points value: {str(e)}")
            return {
                "success": False,
                "result": None,
                "code": "INVALID_POINTS",
                "message": str(e),
                "error_message": str(e)
            }
        except Exception as e:
            logger.error(f"Error adding loyalty points: {str(e)}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "code": "ERROR",
                "message": str(e),
                "error_message": f"System error: {str(e)}"
            }
    
    async def search_transaction(
        self,
        trans_id: Optional[str] = None,
        ref_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search transaction by Mytel's transactionId or partner's refTransId
        
        Args:
            trans_id: Mytel's transaction ID
            ref_id: Partner's reference transaction ID
            
        Returns:
            Dictionary containing search results
        """
        try:
            if not trans_id and not ref_id:
                raise ValueError("Either trans_id or ref_id must be provided")
            
            # Prepare query parameters
            params = {}
            if trans_id:
                params["transId"] = trans_id
            if ref_id:
                params["refId"] = ref_id
            
            # API URL
            url = f"{self.base_url}{self.config.API_SEARCH}"
            
            logger.info(f"Searching transaction with params: {params}")
            
            # Make request with retry
            response = await self._make_request_with_retry(
                method="GET",
                url=url,
                params=params,
                auth=(self.username, self.password)
            )
            
            # Parse response
            result = response.json()
            
            logger.info(f"Search result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching transaction: {str(e)}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "code": "ERROR",
                "message": str(e)
            }
    
    def get_latest_transaction(self, transactions: list) -> Optional[Dict[str, Any]]:
        """
        Get the latest transaction from a list based on createdAt timestamp
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Latest transaction or None if list is empty
        """
        if not transactions:
            return None
        
        try:
            # Sort by createdAt descending
            sorted_trans = sorted(
                transactions,
                key=lambda x: x.get("createdAt", ""),
                reverse=True
            )
            return sorted_trans[0]
        except Exception as e:
            logger.warning(f"Error sorting transactions: {str(e)}. Returning first.")
            return transactions[0]
    
    async def verify_transaction_success(self, ref_trans_id: str) -> bool:
        """
        Verify if a transaction was successful
        
        Args:
            ref_trans_id: Reference transaction ID to check
            
        Returns:
            True if transaction was successful, False otherwise
        """
        try:
            result = await self.search_transaction(ref_id=ref_trans_id)
            
            if not result.get("success"):
                return False
            
            transactions = result.get("result", [])
            if not transactions:
                return False
            
            # Get latest transaction
            latest_trans = self.get_latest_transaction(transactions)
            
            # Check if latest transaction is successful
            return latest_trans.get("status") == "SUCCESS"
            
        except Exception as e:
            logger.error(f"Error verifying transaction: {str(e)}")
            return False    