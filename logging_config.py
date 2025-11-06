# logging_config.py - Đúng theo thiết kế ban đầu
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Cấu hình logging cho toàn bộ ứng dụng"""
    
    # Xác định thư mục logs
    if os.path.exists("/app"):
        log_dir = Path("/app/logs")
    else:
        base_dir = Path(__file__).resolve().parent
        log_dir = base_dir / "logs"

    # Tạo thư mục và set permissions
    log_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(log_dir, 0o755)
    
    # File log chính: herosaga.log (sẽ tự động rotate)
    log_file = log_dir / "herosaga.log"
    
    # Cấu hình formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Xóa handlers cũ nếu có
    root_logger.handlers.clear()
    
    # File handler với rotation
    # Khi midnight: herosaga.log -> herosaga.log.2025-10-17
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_file),
        when='midnight',
        interval=1,
        backupCount=365,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Thêm handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Cấu hình specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    
    # Log thông tin khởi tạo
    logging.info(f"Logging initialized. Log file: {log_file}")
    print(f"Logging configured. Log file: {log_file}")
    
    return str(log_file)