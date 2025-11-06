# utils/redis_gameplay_queue.py - Optional Redis queue cho high-load scenarios
import redis.asyncio as aioredis
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GameplayRedisQueue:
    """
    Optional Redis queue để lưu tạm gameplay logs
    Dùng khi DB quá tải, worker sẽ ghi sau
    
    Theo plan: Redis KHÔNG bắt buộc cho /log-gameplay
    Chỉ dùng khi scale lên hệ thống lớn
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.queue_key = "gameplay:queue"

    async def connect(self):
        """Kết nối Redis"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis gameplay queue")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    async def disconnect(self):
        """Ngắt kết nối"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    async def push_gameplay(self, gameplay_data: Dict[str, Any]) -> bool:
        """
        Đẩy gameplay log vào queue
        Return: True nếu thành công
        """
        if not self.redis:
            logger.warning("Redis not connected, skipping queue push")
            return False

        try:
            # Add timestamp
            gameplay_data["queued_at"] = datetime.utcnow().isoformat()
            
            # Push to Redis list
            await self.redis.rpush(
                self.queue_key,
                json.dumps(gameplay_data)
            )
            
            logger.debug(f"Pushed gameplay to queue: user={gameplay_data.get('user_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to push to Redis queue: {e}")
            return False

    async def pop_gameplay(self) -> Optional[Dict[str, Any]]:
        """
        Lấy 1 gameplay log từ queue (FIFO)
        Worker sẽ gọi hàm này
        """
        if not self.redis:
            return None

        try:
            data = await self.redis.lpop(self.queue_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to pop from Redis queue: {e}")
            return None

    async def get_queue_length(self) -> int:
        """Lấy số lượng items đang chờ trong queue"""
        if not self.redis:
            return 0

        try:
            return await self.redis.llen(self.queue_key)
        except Exception:
            return 0

    async def clear_queue(self):
        """Xóa toàn bộ queue (admin only)"""
        if not self.redis:
            return

        try:
            await self.redis.delete(self.queue_key)
            logger.info("Cleared gameplay queue")
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")


# Worker example (chạy riêng process)
async def gameplay_queue_worker(
    redis_url: str,
    db_session_factory,
    batch_size: int = 50,
    interval_seconds: int = 5
):
    """
    Worker để xử lý gameplay logs từ Redis queue
    Chỉ cần khi hệ thống scale lên
    
    Usage:
        python -m workers.gameplay_worker
    """
    import asyncio
    from services.gameplay_service import GameplayService

    queue = GameplayRedisQueue(redis_url)
    await queue.connect()

    logger.info(f"Gameplay queue worker started (batch={batch_size}, interval={interval_seconds}s)")

    while True:
        try:
            # Check queue length
            queue_len = await queue.get_queue_length()
            if queue_len == 0:
                await asyncio.sleep(interval_seconds)
                continue

            logger.info(f"Processing {min(batch_size, queue_len)} gameplay logs from queue")

            # Process batch
            async with db_session_factory() as db:
                processed = 0
                for _ in range(min(batch_size, queue_len)):
                    gameplay_data = await queue.pop_gameplay()
                    if not gameplay_data:
                        break

                    try:
                        # Insert vào DB
                        await GameplayService.log_gameplay(
                            db=db,
                            user_id=gameplay_data["user_id"],
                            msisdn=gameplay_data["msisdn"],
                            level_code=gameplay_data["level_code"],
                            score=gameplay_data["score"],
                            coins_earned=gameplay_data["coins_earned"],
                            duration_seconds=gameplay_data["duration_seconds"],
                            stars=gameplay_data.get("stars"),
                            items_start=gameplay_data.get("items_start"),
                            items_used=gameplay_data.get("items_used"),
                            items_earned=gameplay_data.get("items_earned"),
                            game_mode=gameplay_data.get("game_mode", "normal")
                        )
                        processed += 1
                    except Exception as e:
                        logger.error(f"Failed to process gameplay log: {e}")
                        # Có thể push lại vào dead letter queue

                logger.info(f"Processed {processed} gameplay logs")

            await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(interval_seconds)


# Singleton instance
_gameplay_queue: Optional[GameplayRedisQueue] = None


async def get_gameplay_queue() -> GameplayRedisQueue:
    """Dependency injection cho FastAPI"""
    global _gameplay_queue
    if _gameplay_queue is None:
        _gameplay_queue = GameplayRedisQueue()
        await _gameplay_queue.connect()
    return _gameplay_queue