# services/myid_crypto.py - FIXED: Using SHA1 for signature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
import logging
from pathlib import Path
from urllib.parse import unquote
from Crypto.Util.Padding import unpad
import re

logger = logging.getLogger(__name__)

# ====== Key Paths Configuration ======
KEY_BASE_PATH = Path("config/key/mytel")

KEY_MAPPING = {
    "SUPER_MATINO_WEEKLY": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_MONTHLY": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_DAILY": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_BUY1": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_BUY2": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_BUY3": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_BUY4": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_BUY5": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"},
    "SUPER_MATINO_BUY6": {"private": "PRIVATE_CP", "public": "PUBLIC_CP", "public_vt": "PUBLIC_VT_CP"}
}

# ====== Load Keys from .pem files ======
def load_private_key(sub_service_name: str):
    """
    Load private key for signing from PRIVATE_CP.pem
    Uses cryptography library for consistency with signing
    """
    key_file = KEY_BASE_PATH / sub_service_name / "PRIVATE_CP.pem"
    
    if not key_file.exists():
        raise FileNotFoundError(f"Private key not found: {key_file}")
    
    with open(key_file, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    
    logger.debug(f"Loaded private key from {key_file}")
    return private_key

def load_public_vt_key_for_encryption(sub_service_name: str):
    """
    Load PUBLIC_VT_CP.pem for RSA encryption
    Uses PyCrypto for encryption to match MPS requirements
    """
    key_file = KEY_BASE_PATH / sub_service_name / "PUBLIC_VT_CP.pem"
    
    if not key_file.exists():
        raise FileNotFoundError(f"Public VT key not found: {key_file}")
    
    with open(key_file, "rb") as f:
        key_data = f.read()
    
    # Import with PyCrypto
    rsa_public_key = RSA.import_key(key_data)
    logger.debug(f"Loaded PUBLIC_VT_CP key: {rsa_public_key.size_in_bits()} bits")
    
    return rsa_public_key

# ====== Step 2: AES Encryption ======
def encrypt_aes(data: str, aes_key: bytes) -> str:
    """
    Encrypt data with AES in ECB mode
    
    Args:
        data: Plain text string to encrypt
        aes_key: 16-byte AES key
        
    Returns:
        Base64 encoded encrypted data
    """
    try:
        cipher = AES.new(aes_key, AES.MODE_ECB)
        padded_data = pad(data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
        
        logger.debug(f"AES Encryption:")
        logger.debug(f"  Input length: {len(data)} bytes")
        logger.debug(f"  Padded length: {len(padded_data)} bytes")
        logger.debug(f"  Encrypted (base64): {encrypted_b64[:50]}...")
        
        return encrypted_b64
        
    except Exception as e:
        logger.error(f"AES encryption error: {str(e)}")
        raise

# ====== Step 3: RSA Encryption ======
def encrypt_rsa(data: str, public_key_vt) -> str:
    """
    Encrypt data with RSA public key (PUBLIC_VT_CP.pem)
    
    Args:
        data: String to encrypt (usually "value=...&key=...")
        public_key_vt: RSA public key object from PyCrypto
        
    Returns:
        Base64 encoded encrypted data
    """
    try:
        cipher = PKCS1_v1_5.new(public_key_vt)
        data_bytes = data.encode('utf-8')
        
        # Check size limit
        max_size = public_key_vt.size_in_bytes() - 11  # PKCS1 padding overhead
        if len(data_bytes) > max_size:
            raise ValueError(
                f"Data too large for RSA: {len(data_bytes)} > {max_size} bytes"
            )
        
        encrypted = cipher.encrypt(data_bytes)
        encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
        
        logger.debug(f"RSA Encryption:")
        logger.debug(f"  Key size: {public_key_vt.size_in_bits()} bits")
        logger.debug(f"  Max payload: {max_size} bytes")
        logger.debug(f"  Actual payload: {len(data_bytes)} bytes")
        logger.debug(f"  Encrypted (base64): {encrypted_b64[:50]}...")
        
        return encrypted_b64
        
    except Exception as e:
        logger.error(f"RSA encryption error: {str(e)}")
        raise

# ====== Step 4: Create Signature ======
def create_msg_signature(data: str, private_key) -> str:
    """
    Create signature for authentication using SHA1+RSA
    CRITICAL: Must use SHA1 to match MPS Java implementation (SHA1withRSA)
    
    Args:
        data: String to sign (the RSA encrypted DATA parameter)
        private_key: Private key from cryptography library
        
    Returns:
        Base64 encoded signature
    """
    try:
        signature = private_key.sign(
            data.encode('utf-8'),
            asym_padding.PKCS1v15(),
            hashes.SHA1()  # FIXED: Changed from SHA256 to SHA1 to match Java code
        )
        
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        logger.debug(f"Signature Creation (SHA1withRSA):")
        logger.debug(f"  Algorithm: SHA1withRSA (matching Java implementation)")
        logger.debug(f"  Data length: {len(data)} chars")
        logger.debug(f"  Signature (base64): {signature_b64[:50]}...")
        
        return signature_b64
        
    except Exception as e:
        logger.error(f"Signature creation error: {str(e)}")
        raise

# ====== Complete Encryption Flow (Steps 1-4) ======
def encrypt_with_mps_public_key_v2(sub_service_name: str, data: str, step: int = 2) -> dict:
    """
    Complete encryption flow following MPS guideline:
    
    Step 1: input = raw data string
    Step 2: input_with_key_AES = f"value={encryptAES(input, keyAES)}&key={keyAES}"
    Step 3: data_encrypted_RSA = encryptRSA(input_with_key_AES, publicKeyViettel)
    Step 4: signature = createMsgSignature(data_encrypted_RSA, privateKeyCP) [SHA1withRSA]
    
    Args:
        sub_service_name: Service name for key lookup
        data: Raw input string (Step 1 format)
        step: Current step number for logging
        
    Returns:
        dict with all encryption details
    """
    try:
        logger.info("=" * 80)
        logger.info(f"ENCRYPTION FLOW FOR: {sub_service_name}")
        logger.info("=" * 80)
        
        # STEP 1: Input data (already provided)
        logger.info(f"Step 1: Input data")
        logger.info(f"  {data}")
        
        # STEP 2: Encrypt with AES and build value=...&key=...
        logger.info(f"\nStep 2: AES Encryption")
        
        # Generate random 16-byte AES key
        aes_key = get_random_bytes(16)
        aes_key_hex = aes_key.hex()
        logger.info(f"  Generated AES key (hex): {aes_key_hex}")
        
        # Encrypt input with AES
        encrypted_value = encrypt_aes(data, aes_key)
        logger.info(f"  Encrypted value (base64): {encrypted_value[:50]}...")
        
        # Build combined string: value=...&key=...
        input_with_key_aes = f"value={encrypted_value}&key={aes_key_hex}"
        logger.info(f"  Combined string length: {len(input_with_key_aes)} bytes")
        
        # STEP 3: Encrypt combined string with RSA
        logger.info(f"\nStep 3: RSA Encryption")
        
        # Load Viettel public key
        public_key_vt = load_public_vt_key_for_encryption(sub_service_name)
        
        # Encrypt with RSA
        data_encrypted_rsa = encrypt_rsa(input_with_key_aes, public_key_vt)
        logger.info(f"  DATA parameter ready: {data_encrypted_rsa[:50]}...")
        
        # STEP 4: Create signature (SHA1withRSA)
        logger.info(f"\nStep 4: Create Signature")
        
        # Load private key
        private_key = load_private_key(sub_service_name)
        
        # Sign the encrypted data (using SHA1withRSA to match Java implementation)
        signature = create_msg_signature(data_encrypted_rsa, private_key)
        logger.info(f"  Algorithm: SHA1withRSA (matching MPS requirements)")
        logger.info(f"  SIG parameter ready: {signature[:50]}...")
        
        logger.info("\n" + "=" * 80)
        logger.info("ENCRYPTION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        return {
            "aes_key_hex": aes_key_hex,
            "aes_encrypted_base64": encrypted_value,
            "combined_string": input_with_key_aes,
            "rsa_encrypted_base64": data_encrypted_rsa,
            "signature_base64": signature,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Encryption flow error: {str(e)}", exc_info=True)
        raise

def encrypt_with_mps_public_key(sub_service_name: str, data: str) -> str:
    """
    Legacy function - returns only the encrypted data
    For backward compatibility
    """
    result = encrypt_with_mps_public_key_v2(sub_service_name, data)
    return result["rsa_encrypted_base64"]

# ====== Signing Functions (for compatibility) ======
def sign_data_v2(data: str, private_key) -> dict:
    """
    Sign data with private key using SHA1withRSA
    Wrapper around create_msg_signature for compatibility
    """
    signature = create_msg_signature(data, private_key)
    
    return {
        "signature_base64": signature,
        "data_length": len(data),
        "algorithm": "SHA1withRSA",
        "success": True
    }

def sign_data(data: str, private_key) -> str:
    """
    Legacy function - returns only the signature
    """
    return create_msg_signature(data, private_key)

# ====== Utility Functions ======
import time
import random

def generate_session_id() -> str:
    """Generate session ID (millisecond timestamp)"""
    return str(int(time.time() * 1000))

def generate_request_id() -> str:
    """Generate request ID (random 11-digit number)"""
    return str(random.randint(10000000000, 99999999999))

def build_raw_input(
    msisdn: str,
    sub_service: str,
    session_id: str = None,
    request_id: str = None
) -> str:
    """
    Build raw input data string (Step 1)
    
    Format: CATE=BLANK&SUB={sub}&ITEM=NULL&SUB_CP=null&SESS={sess}&
            PRICE=0&SOURCE=CLIENT&IMEI=NULL&CONT=null&TYPE=MOBILE&
            MOBILE={mobile}&REQ={req}
    """
    if session_id is None:
        session_id = generate_session_id()
    
    if request_id is None:
        request_id = generate_request_id()
    
    raw_input = (
        f"CATE=BLANK&SUB={sub_service}&ITEM=NULL&SUB_CP=null&"
        f"SESS={session_id}&PRICE=0&SOURCE=CLIENT&IMEI=NULL&"
        f"CONT=null&TYPE=MOBILE&MOBILE={msisdn}&REQ={request_id}"
    )
    
    return raw_input

# ====== Validation Functions ======
def validate_key_setup(sub_service_name: str) -> dict:
    """Validate all required keys are present and working"""
    results = {
        "sub_service": sub_service_name,
        "private_key": False,
        "public_vt_key": False,
        "errors": []
    }
    
    try:
        # Check private key
        private_key = load_private_key(sub_service_name)
        key_size = private_key.key_size
        results["private_key"] = True
        results["private_key_size"] = key_size
        logger.info(f"✓ Private key loaded: {key_size} bits")
    except Exception as e:
        results["errors"].append(f"Private key error: {str(e)}")
        logger.error(f"✗ Private key failed: {str(e)}")
    
    try:
        # Check public VT key
        rsa_key = load_public_vt_key_for_encryption(sub_service_name)
        key_size = rsa_key.size_in_bits()
        results["public_vt_key"] = True
        results["public_vt_key_size"] = key_size
        logger.info(f"✓ Public VT key loaded: {key_size} bits")
    except Exception as e:
        results["errors"].append(f"Public VT key error: {str(e)}")
        logger.error(f"✗ Public VT key failed: {str(e)}")
    
    results["valid"] = results["private_key"] and results["public_vt_key"]
    
    return results

# ====== Testing Functions ======
def test_full_encryption_flow(sub_service_name: str, test_data: str = None):
    """
    Test complete encryption and signing flow
    Follows the exact guideline: Steps 1-4 with SHA1withRSA
    """
    try:
        if test_data is None:
            session_id = generate_session_id()
            request_id = generate_request_id()
            test_data = build_raw_input(
                msisdn="959696783333",
                sub_service=sub_service_name,
                session_id=session_id,
                request_id=request_id
            )
        
        logger.info("\n" + "=" * 80)
        logger.info("TESTING FULL ENCRYPTION FLOW (SHA1withRSA)")
        logger.info("=" * 80)
        
        # Run the complete encryption flow
        result = encrypt_with_mps_public_key_v2(sub_service_name, test_data)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✓ All steps completed successfully")
        logger.info(f"✓ Using SHA1withRSA for signature (matching Java)")
        logger.info(f"✓ Data ready to send to MPS")
        logger.info(f"  - Original data length: {len(test_data)}")
        logger.info(f"  - AES key: {result['aes_key_hex']}")
        logger.info(f"  - DATA parameter length: {len(result['rsa_encrypted_base64'])}")
        logger.info(f"  - SIG parameter length: {len(result['signature_base64'])}")
        
        return {
            "success": True,
            "encrypted_data": result['rsa_encrypted_base64'],
            "signature": result['signature_base64'],
            "details": {
                "aes_key": result['aes_key_hex'],
                "original_length": len(test_data),
                "encrypted_length": len(result['rsa_encrypted_base64']),
                "signature_length": len(result['signature_base64']),
                "signature_algorithm": "SHA1withRSA"
            }
        }
        
    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

def test_sign_verify(sub_service_name: str):
    """
    Test signing with sample data using SHA1withRSA
    """
    try:
        logger.info("\n" + "=" * 80)
        logger.info("TESTING SIGNATURE CREATION (SHA1withRSA)")
        logger.info("=" * 80)
        
        # Load private key
        private_key = load_private_key(sub_service_name)
        
        # Test data
        test_data = f"test_data_12345_{int(time.time())}"
        
        # Sign
        logger.info(f"Signing test data: {test_data}")
        signature = create_msg_signature(test_data, private_key)
        
        logger.info(f"\n✓ Signature created successfully")
        logger.info(f"  Algorithm: SHA1withRSA (matching Java)")
        logger.info(f"  Test data: {test_data}")
        logger.info(f"  Signature: {signature[:50]}...")
        logger.info(f"  Signature length: {len(signature)} chars")
        
        return {
            "success": True,
            "test_data": test_data,
            "signature": signature,
            "signature_length": len(signature),
            "algorithm": "SHA1withRSA",
            "note": "Signature created successfully. MPS will verify on their side."
        }
        
    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
def decrypt_with_mps_private_key_v2(sub_service_name: str, response_text: str) -> str:
    """
    Decrypt MPS response (Java EncryptUtil compatible)
    - Step 1: RSA decrypt (PKCS#1 v1.5)
    - Step 2: Parse VALUE=...&KEY=...
    - Step 3: AES decrypt VALUE using KEY (ECB mode)
    """
    try:
        logger.info("🔽 [MPS-DECODE] Start decrypting response (v2)")
        logger.info(f"Raw response text: {response_text[:120]}")

        # --- STEP 1: Clean up response format ---
        raw_text = response_text.strip()
        if raw_text.startswith("DATA="):
            match = re.match(r"DATA=([^&]*)(?:&SIG=.*)?", raw_text)
            if not match:
                raise ValueError("Invalid MPS response format: missing DATA field")
            data_encrypted = match.group(1)
        else:
            data_encrypted = raw_text

        # Fix base64 padding
        if len(data_encrypted) % 4:
            data_encrypted += "=" * (4 - len(data_encrypted) % 4)

        # --- STEP 2: Load private key ---
        base_dir = KEY_BASE_PATH / sub_service_name
        private_cp_path = base_dir / "PRIVATE_CP.pem"
        if not private_cp_path.exists():
            raise FileNotFoundError(f"Private key not found: {private_cp_path}")

        private_key = RSA.import_key(open(private_cp_path, "rb").read())

        # --- STEP 3: RSA decrypt using PKCS#1 v1.5 ---
        cipher_rsa = PKCS1_v1_5.new(private_key)
        decrypted_bytes = cipher_rsa.decrypt(base64.b64decode(data_encrypted), None)
        if not decrypted_bytes:
            raise ValueError("RSA decryption failed or empty result")

        decrypted_str = decrypted_bytes.decode("utf-8", errors="ignore").strip()
        logger.info(f"🔍 RSA decrypted string:\n{decrypted_str}")

        # --- STEP 4: Parse VALUE and KEY ---
        if "&" not in decrypted_str:
            # Một số MPS chỉ trả VALUE=... mà không có KEY
            match = re.search(r"VALUE=([A-Za-z0-9+/=]+)", decrypted_str, re.IGNORECASE)
            if match:
                value_enc = match.group(1)
                logger.warning("⚠️ MPS response only contains VALUE=..., no AES key. Trying default key.")
                # Dùng lại AES key của request (nếu bạn lưu tạm)
                return value_enc
            else:
                raise ValueError(f"Invalid RSA decrypted structure: {decrypted_str[:120]}")

        parts = decrypted_str.split("&")
        value_enc = parts[0].split("=")[1].strip()
        key_hex = parts[1].split("=")[1].strip()

        logger.info(f"🔑 AES key (hex): {key_hex}")
        logger.info(f"📦 AES value (base64): {value_enc[:100]}...")

        # Fix base64 padding for AES
        if len(value_enc) % 4:
            value_enc += "=" * (4 - len(value_enc) % 4)

        # --- STEP 5: AES decrypt (ECB) ---
        aes_key = bytes.fromhex(key_hex)
        cipher_aes = AES.new(aes_key, AES.MODE_ECB)
        decrypted_bytes = cipher_aes.decrypt(base64.b64decode(value_enc))

        # Một số MPS không pad chuẩn, nên ta cố gắng unpad an toàn
        try:
            plain = unpad(decrypted_bytes, AES.block_size).decode("utf-8", errors="ignore").strip()
        except Exception:
            plain = decrypted_bytes.decode("utf-8", errors="ignore").strip()

        logger.info(f"✅ Final decrypted MPS text:\n{plain}")
        return plain

    except Exception as e:
        logger.error(f"❌ Error decrypting MPS response: {e}", exc_info=True)
        raise


def decrypt_mps_response(sub_service_name: str, response_text: str) -> str:
    """
    Legacy wrapper for compatibility.
    Redirects to decrypt_with_mps_private_key_v2() and keeps old log format.
    """
    logger.info("🔽 [MPS-DECODE] Using legacy decrypt_mps_response()")
    try:
        plain = decrypt_with_mps_private_key_v2(sub_service_name, response_text)
        logger.info(f"✅ Legacy decrypt successful:\n{plain}")
        return plain
    except Exception as e:
        logger.error(f"❌ Legacy decrypt failed: {e}")
        raise
    
# ====== Export commonly used functions ======
__all__ = [
    'load_private_key',
    'load_public_vt_key_for_encryption',
    'encrypt_aes',
    'encrypt_rsa',
    'create_msg_signature',
    'encrypt_with_mps_public_key',
    'encrypt_with_mps_public_key_v2',
    'sign_data',
    'sign_data_v2',
    'build_raw_input',
    'generate_session_id',
    'generate_request_id',
    'validate_key_setup',
    'test_full_encryption_flow',
    'test_sign_verify',
    'KEY_BASE_PATH'
]