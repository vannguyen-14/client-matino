# services/gameplay_service.py - Service layer for gameplay logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, desc
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import logging

from models.models import GameplayHistory, User

logger = logging.getLogger(__name__)
UTC = timezone.utc


class GameplayService:
    """
    Service layer cho gameplay history
    Xử lý logic nghiệp vụ, tách biệt khỏi router
    """

    @staticmethod
    async def calculate_next_attempt(
        db: AsyncSession,
        user_id: int,
        level_code: str
    ) -> int:
        """
        Tính số lần chơi tiếp theo cho user-level cụ thể
        """
        query = select(
            func.coalesce(func.max(GameplayHistory.play_attempt), 0) + 1
        ).where(
            and_(
                GameplayHistory.user_id == user_id,
                GameplayHistory.level_code == level_code
            )
        )
        result = await db.execute(query)
        return result.scalar() or 1

    @staticmethod
    async def log_gameplay(
        db: AsyncSession,
        user_id: int,
        msisdn: str,
        level_code: str,
        score: int,
        coins_earned: int,
        duration_seconds: int,
        stars: Optional[int] = None,
        items_start: Optional[Dict[str, int]] = None,
        items_used: Optional[Dict[str, int]] = None,
        items_earned: Optional[Dict[str, int]] = None,
        game_mode: str = "normal"
    ) -> GameplayHistory:
        """
        Ghi log gameplay - chỉ insert, không tính delta
        """
        # Tính play_attempt
        next_attempt = await GameplayService.calculate_next_attempt(
            db, user_id, level_code
        )

        # Prepare JSON fields
        items_start_json = json.dumps(items_start) if items_start else None
        items_used_json = json.dumps(items_used) if items_used else None
        items_earned_json = json.dumps(items_earned) if items_earned else None

        # Tạo record
        now = datetime.now(UTC)
        gameplay = GameplayHistory(
            user_id=user_id,
            msisdn=msisdn,
            level_code=level_code,
            play_attempt=next_attempt,
            score=score,
            coins_earned=coins_earned,
            stars=stars,
            started_at=now,
            duration_seconds=duration_seconds,
            items_start=items_start_json,
            items_used=items_used_json,
            items_earned=items_earned_json,
            game_mode=game_mode,
            created_at=now
        )

        db.add(gameplay)
        await db.commit()
        await db.refresh(gameplay)

        logger.info(
            f"Logged gameplay: user={user_id}, level={level_code}, "
            f"attempt={next_attempt}, score={score}, coins={coins_earned}"
        )

        return gameplay

    @staticmethod
    async def get_user_stats(
        db: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Lấy thống kê gameplay của user trong khoảng thời gian
        """
        query = select(
            func.count(GameplayHistory.id).label('total_games'),
            func.sum(GameplayHistory.score).label('total_score'),
            func.sum(GameplayHistory.coins_earned).label('total_coins'),
            func.avg(GameplayHistory.duration_seconds).label('avg_duration'),
            func.count(func.distinct(GameplayHistory.level_code)).label('unique_levels')
        ).where(
            and_(
                GameplayHistory.user_id == user_id,
                GameplayHistory.started_at >= start_date,
                GameplayHistory.started_at <= end_date
            )
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            return {
                "total_games": 0,
                "total_score": 0,
                "total_coins": 0,
                "avg_duration_seconds": 0.0,
                "unique_levels": 0
            }

        return {
            "total_games": row.total_games or 0,
            "total_score": int(row.total_score or 0),
            "total_coins": int(row.total_coins or 0),
            "avg_duration_seconds": round(float(row.avg_duration or 0), 2),
            "unique_levels": row.unique_levels or 0
        }

    @staticmethod
    async def get_level_leaderboard(
        db: AsyncSession,
        level_code: str,
        limit: int = 10
    ) -> list:
        """
        Lấy top performers cho level cụ thể
        """
        query = select(
            GameplayHistory.user_id,
            User.msisdn,
            User.display_name,
            func.max(GameplayHistory.score).label('best_score'),
            func.max(GameplayHistory.stars).label('best_stars'),
            func.min(GameplayHistory.duration_seconds).label('fastest_time')
        ).join(
            User, User.id == GameplayHistory.user_id
        ).where(
            GameplayHistory.level_code == level_code
        ).group_by(
            GameplayHistory.user_id,
            User.msisdn,
            User.display_name
        ).order_by(
            desc('best_score')
        ).limit(limit)

        result = await db.execute(query)
        return result.all()

    @staticmethod
    def safe_json_load(val: Optional[str]) -> Optional[Dict]:
        """
        Safely load JSON string to dict
        """
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(val)
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return None

    @staticmethod
    def mask_msisdn(msisdn: Optional[str]) -> str:
        """
        Ẩn số điện thoại để bảo mật
        """
        if not msisdn or len(msisdn) <= 4:
            return "****"
        return f"{msisdn[:-4]}****"