# config/mytel_bonus_config.py
import os
from dotenv import load_dotenv

load_dotenv()

class MytelBonusConfig:
    """Configuration for Mytel VAS Partner Gateway"""
    
    # Environment: 'UAT' or 'PRODUCTION'
    ENVIRONMENT = os.getenv("MYTEL_BONUS_ENV", "PRODUCTION")
    
    # Base URLs
    # BASE_URL_UAT = "https://mytelapigw.mytel.com.mm/uat/vas-gw/"
    # Production hiện dùng IP nội bộ theo Mytel cung cấp
    BASE_URL_PROD = "http://10.201.5.123:9350/vas-gw/"
    
    @classmethod
    def get_base_url(cls) -> str:
        """Get base URL based on environment"""
        if cls.ENVIRONMENT == "PRODUCTION":
            return cls.BASE_URL_PROD
        return cls.BASE_URL_UAT
    
    # Authentication credentials (production)
    USERNAME = os.getenv("MYTEL_BONUS_USERNAME", "HERO_SAGA")
    PASSWORD = os.getenv("MYTEL_BONUS_PASSWORD", "HeroSaga123KKKs!jmkK")
    SECRET_KEY = os.getenv("MYTEL_BONUS_SECRET", "HeroSaga2025Mytel123")
    
    # API Endpoints
    API_ADD_PRIZE = "api/v1/add-prize"
    API_SEARCH = "api/v1/search"
    
    # Package codes for loyalty points
    LOYALTY_PACKAGES = {
        300: "LOYALTY_300",
        500: "LOYALTY_500",
        700: "LOYALTY_700",
        1000: "LOYALTY_1000",
        1500: "LOYALTY_1500",
        2000: "LOYALTY_2000",
        4500: "LOYALTY_4500",
        7000: "LOYALTY_7000",
        8000: "LOYALTY_8000",
        10000: "LOYALTY_10000"
    }
    
    # Timeout settings
    REQUEST_TIMEOUT = 30  # seconds
    
    @classmethod
    def get_package_code(cls, points: int) -> str:
        """
        Get package code for loyalty points
        
        Args:
            points: Number of loyalty points
            
        Returns:
            Package code string
            
        Raises:
            ValueError: If points amount is not supported
        """
        if points not in cls.LOYALTY_PACKAGES:
            raise ValueError(
                f"Unsupported loyalty points: {points}. "
                f"Available: {list(cls.LOYALTY_PACKAGES.keys())}"
            )
        return cls.LOYALTY_PACKAGES[points]
