# config/myid_config.py
from pydantic import BaseSettings
from typing import Dict, List

class MyIDSettings(BaseSettings):
    # MPS Authentication
    MPS_USERNAME: str = "your_username"
    MPS_PASSWORD: str = "your_password"
    
    # Service IDs mapping
    SERVICE_IDS: Dict[str, str] = {
        "DAILY": "SERVICE_NAME_DAILY",
        "WEEKLY": "SERVICE_NAME_WEEKLY", 
        "MONTHLY": "SERVICE_NAME_MONTHLY",
        "OTP": "SERVICE_NAME_OTP"
    }
    
    # Package pricing (MMK)
    PACKAGE_PRICES: Dict[str, int] = {
        "DAILY": 149,
        "WEEKLY": 599,
        "MONTHLY": 1999,
        "OTP": 99
    }
    
    # Valid channels
    VALID_CHANNELS: List[str] = ["SMS", "USSD", "CP", "APP", "WEB", "WAP"]
    
    # Status codes
    STATUS_CODES: Dict[str, int] = {
        "INACTIVE": 0,
        "ACTIVE": 1, 
        "PENDING": 2,
        "CANCELLED": 3
    }
    
    # Charging status codes
    CHARGING_STATUS: Dict[str, int] = {
        "RENEWAL": 0,
        "REGISTER": 1,
        "PENDING_CONFIRM": 2,
        "CANCEL": 3
    }
    
    # Timeout settings
    MPS_TIMEOUT: int = 30  # seconds
    
    # Logging
    ENABLE_REQUEST_LOGGING: bool = True
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

# Global settings instance
myid_settings = MyIDSettings()

# Helper functions
def get_package_price(package_name: str) -> int:
    """Get price for a package"""
    return myid_settings.PACKAGE_PRICES.get(package_name.upper(), 0)

def get_service_id(package_name: str) -> str:
    """Get service ID for a package"""
    return myid_settings.SERVICE_IDS.get(package_name.upper(), package_name)

def is_valid_channel(channel: str) -> bool:
    """Check if channel is valid"""
    return channel.upper() in myid_settings.VALID_CHANNELS

# Package configuration
PACKAGE_CONFIGS = {
    "DAILY": {
        "name": "Daily Package",
        "duration_days": 1,
        "price": 149,
        "description": "1 day unlimited access"
    },
    "WEEKLY": {
        "name": "Weekly Package", 
        "duration_days": 7,
        "price": 599,
        "description": "7 days unlimited access"
    },
    "MONTHLY": {
        "name": "Monthly Package",
        "duration_days": 30,
        "price": 1999,
        "description": "30 days unlimited access"
    },
    "OTP": {
        "name": "One-Time Package",
        "duration_days": 0,
        "price": 99,
        "description": "One-time purchase"
    }
}

# Response messages
RESPONSE_MESSAGES = {
    "REGISTER_SUCCESS": "Ban da dang ky thanh cong",
    "REGISTER_FAILED": "Dang ky that bai",
    "CANCEL_SUCCESS": "Ban da huy thanh cong", 
    "CANCEL_FAILED": "Huy dich vu that bai",
    "RENEWAL_SUCCESS": "Gia han thanh cong",
    "RENEWAL_FAILED": "Gia han that bai",
    "OTP_SUCCESS": "Mua goi thanh cong",
    "OTP_FAILED": "Mua goi that bai"
}

def get_response_message(action: str, success: bool = True) -> str:
    """Get localized response message"""
    key = f"{action.upper()}_{'SUCCESS' if success else 'FAILED'}"
    return RESPONSE_MESSAGES.get(key, "")

# Validation rules
MSISDN_PATTERNS = {
    "MYANMAR": r"^959\d{8,9}$",
    "BANGLADESH": r"^880\d{8,9}$"
}

TRANSACTION_ID_PATTERNS = {
    "SMS": r"^07000002\d{14,20}$",
    "USSD": r"^W12-\d+-\d+$",
    "RENEWAL": r"^04000002\d{14,20}$"
}

def validate_msisdn(msisdn: str, country: str = "MYANMAR") -> bool:
    """Validate phone number format"""
    import re
    pattern = MSISDN_PATTERNS.get(country.upper(), MSISDN_PATTERNS["MYANMAR"])
    return bool(re.match(pattern, msisdn))

def validate_transaction_id(transaction_id: str, channel: str) -> bool:
    """Validate transaction ID format"""
    import re
    if channel.upper() == "SMS":
        return bool(re.match(TRANSACTION_ID_PATTERNS["SMS"], transaction_id))
    elif channel.upper() == "USSD":
        return bool(re.match(TRANSACTION_ID_PATTERNS["USSD"], transaction_id))
    elif channel.upper() == "CP":
        return bool(re.match(TRANSACTION_ID_PATTERNS["RENEWAL"], transaction_id))
    return True  # Allow other formats