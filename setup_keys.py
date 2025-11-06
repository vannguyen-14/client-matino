# setup_keys.py - Script để setup và validate keys
"""
Script để setup key structure từ CSV file bạn cung cấp

Structure:
config/
  key/
    mytel/
      SUPER_MATINO_WEEKLY/
        PRIVATE_CP.key
        PUBLIC_CP.crt
        PUBLIC_VT_CP.crt
      SUPER_MATINO_MONTHLY/
        ...
"""

import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base path for keys
KEY_BASE_PATH = Path("config/key/mytel")

def setup_keys_from_csv(csv_path: str):
    """
    Đọc CSV và tạo key files
    """
    try:
        # Read CSV
        df = pd.read_csv(csv_path, sep='\t')  # Assuming tab-separated
        
        logger.info(f"Found {len(df)} services in CSV")
        
        for _, row in df.iterrows():
            service_name = row['SERVICE_NAME']
            sub_service = row['SUB_SERVICE_NAME']
            
            # Create directory
            service_dir = KEY_BASE_PATH / sub_service
            service_dir.mkdir(parents=True, exist_ok=True)
            
            # Write private key
            if pd.notna(row['PRIVATE_CP']):
                private_key_file = service_dir / "PRIVATE_CP.key"
                with open(private_key_file, 'w') as f:
                    f.write(row['PRIVATE_CP'])
                logger.info(f"Created: {private_key_file}")
            
            # Write public key
            if pd.notna(row['PUBLIC_CP']):
                public_key_file = service_dir / "PUBLIC_CP.crt"
                with open(public_key_file, 'w') as f:
                    f.write(row['PUBLIC_CP'])
                logger.info(f"Created: {public_key_file}")
            
            # Write public VT key
            if pd.notna(row['PUBLIC_VT_CP']):
                public_vt_key_file = service_dir / "PUBLIC_VT_CP.crt"
                with open(public_vt_key_file, 'w') as f:
                    f.write(row['PUBLIC_VT_CP'])
                logger.info(f"Created: {public_vt_key_file}")
        
        logger.info("Key setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up keys: {str(e)}")
        return False

def validate_all_keys():
    """
    Validate all key setups
    """
    from services.myid_crypto import validate_key_setup, KEY_MAPPING
    
    results = []
    for sub_service in KEY_MAPPING.keys():
        result = validate_key_setup(sub_service)
        results.append(result)
        
        status = "✓ VALID" if result["valid"] else "✗ INVALID"
        logger.info(f"{status}: {sub_service}")
        
        if result["errors"]:
            for error in result["errors"]:
                logger.error(f"  - {error}")
    
    return results

def manual_key_setup():
    """
    Hướng dẫn setup keys thủ công
    """
    instructions = """
    CÁC BƯỚC SETUP KEYS THỦ CÔNG:
    
    1. Tạo cấu trúc thư mục:
       mkdir -p config/key/mytel/SUPER_MATINO_WEEKLY
       mkdir -p config/key/mytel/SUPER_MATINO_MONTHLY
       mkdir -p config/key/mytel/SUPER_MATINO_DAILY
       mkdir -p config/key/mytel/SUPER_MATINO_BUY{1..6}
    
    2. Copy keys từ CSV vào các file:
       Mỗi thư mục cần 3 files:
       - PRIVATE_CP.key (Private key)
       - PUBLIC_CP.crt (Public key của CP)
       - PUBLIC_VT_CP.crt (Public key của VT)
    
    3. Format của key files:
       -----BEGIN RSA PRIVATE KEY-----
       ... (content) ...
       -----END RSA PRIVATE KEY-----
       
       -----BEGIN PUBLIC KEY-----
       ... (content) ...
       -----END PUBLIC KEY-----
    
    4. Set permissions (Linux/Mac):
       chmod 600 config/key/mytel/*/PRIVATE_CP.key
       chmod 644 config/key/mytel/*/PUBLIC_*.crt
    
    5. Validate:
       python setup_keys.py --validate
    """
    print(instructions)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--validate":
            validate_all_keys()
        elif sys.argv[1] == "--manual":
            manual_key_setup()
        elif sys.argv[1] == "--csv":
            if len(sys.argv) > 2:
                setup_keys_from_csv(sys.argv[2])
            else:
                print("Usage: python setup_keys.py --csv <csv_file_path>")
    else:
        print("Usage:")
        print("  python setup_keys.py --csv <csv_file>  : Setup from CSV")
        print("  python setup_keys.py --validate        : Validate keys")
        print("  python setup_keys.py --manual          : Show manual setup guide")