# routers/gameplay_history.py - Updated với route structure tối ưu
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func, and_, text
from datetime import datetime, date, timedelta, timezone
from typing import Optional
import json

from models.models import GameplayHistory, User, GameStatement
from schemas.gameplay_schemas import (
    GameplayLogRequest,
    GameplayLogSuccessResponse,
    GameplayHistoryResponse,
    GameplayStatsResponse,
    LevelLeaderboardResponse
)
from database import get_db
from utils.auth_helper import get_user_from_auth
from fastapi.responses import JSONResponse
from config_sys import MYANMAR_TZ

router = APIRouter()
UTC = MYANMAR_TZ

# ============ API: Log Gameplay ============
@router.post("/log-gameplay", response_model=GameplayLogSuccessResponse)
async def log_gameplay(
    payload: GameplayLogRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    API mới dành riêng cho việc ghi chi tiết từng lượt chơi
    - FE gọi API này mỗi khi user hoàn thành một màn
    - Dữ liệu chỉ chứa thông tin về lượt chơi vừa xong
    - Không cần tính delta, chỉ insert record
    """
    # Xác thực user
    user = await get_user_from_auth(payload.auth, db)
    if isinstance(user, JSONResponse):
        return user

    # Tính play_attempt tự động
    query = select(func.coalesce(func.max(GameplayHistory.play_attempt), 0) + 1).where(
        and_(
            GameplayHistory.user_id == user.id,
            GameplayHistory.level_code == payload.level_code
        )
    )
    result = await db.execute(query)
    next_attempt = result.scalar() or 1

    # Prepare JSON fields
    items_start_json = json.dumps(payload.items_start) if payload.items_start else None
    items_used_json = json.dumps(payload.items_used) if payload.items_used else None
    items_earned_json = json.dumps(payload.items_earned) if payload.items_earned else None

    # Tạo record mới (chỉ insert, không so sánh)
    now = datetime.now(UTC)
    gameplay = GameplayHistory(
        user_id=user.id,
        msisdn=user.msisdn or "",
        level_code=payload.level_code,
        play_attempt=next_attempt,
        score=payload.score,
        coins_earned=payload.coins_earned,
        stars=payload.stars,
        started_at=now,
        duration_seconds=payload.duration_seconds,
        items_start=items_start_json,
        items_used=items_used_json,
        items_earned=items_earned_json,
        game_mode=payload.game_mode,
        created_at=now
    )

    db.add(gameplay)
    await db.commit()
    await db.refresh(gameplay)

    return GameplayLogSuccessResponse(
        status="success",
        message="Gameplay logged successfully",
        gameplay_id=gameplay.id
    )


# ============ API: Get All Gameplay History (Main endpoint) ============
@router.get("/gameplay-history", response_model=GameplayHistoryResponse)
async def get_all_gameplay_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    level_code: Optional[str] = None,
    user_id: Optional[int] = None,
    game_mode: Optional[str] = Query(None, regex="^(normal|event)$"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy toàn bộ lịch sử gameplay (main endpoint cho CMS)
    - Mặc định load tất cả records
    - Có thể filter theo user_id, level_code, ngày, game_mode
    """
    sub_latest_statement = (
        select(func.max(GameStatement.id))
        .where(GameStatement.user_id == GameplayHistory.user_id)
        .correlate(GameplayHistory)
        .scalar_subquery()
    )

    query = (
        select(
            GameplayHistory,
            User.msisdn,
            func.JSON_UNQUOTE(
                func.JSON_EXTRACT(GameStatement.statement_json, "$.name")
            ).label("player_name")
        )
        .join(User, User.id == GameplayHistory.user_id)
        .join(
            GameStatement,
            and_(
                GameStatement.user_id == GameplayHistory.user_id,
                GameStatement.id == sub_latest_statement   # ✅ chỉ lấy dòng mới nhất
            ),
            isouter=True
        )
    )
    
    # Optional filters
    if user_id:
        query = query.where(GameplayHistory.user_id == user_id)
    if level_code:
        query = query.where(GameplayHistory.level_code == level_code)
    if game_mode:
        query = query.where(GameplayHistory.game_mode == game_mode)
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.where(GameplayHistory.started_at >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format")
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.where(GameplayHistory.started_at <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    result = await db.execute(
        query.order_by(desc(GameplayHistory.started_at)).limit(limit).offset(offset)
    )
    rows = result.all()

    def _safe_json_load(val):
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(val)
        except Exception:
            return None

    return GameplayHistoryResponse(
        status="success",
        total=total,
        limit=limit,
        offset=offset,
        data=[
            {
                "id": h.GameplayHistory.id,
                "user_id": h.GameplayHistory.user_id,
                "name": h.player_name or "N/A",
                "msisdn": h.msisdn or "N/A",
                "level_code": h.GameplayHistory.level_code,
                "play_attempt": h.GameplayHistory.play_attempt,
                "score": h.GameplayHistory.score,
                "coins_earned": h.GameplayHistory.coins_earned,
                "stars": h.GameplayHistory.stars,
                "duration_seconds": h.GameplayHistory.duration_seconds,
                "items_start": _safe_json_load(h.GameplayHistory.items_start),
                "items_used": _safe_json_load(h.GameplayHistory.items_used),
                "items_earned": _safe_json_load(h.GameplayHistory.items_earned),
                "game_mode": h.GameplayHistory.game_mode,
                "started_at": h.GameplayHistory.started_at.isoformat() if h.GameplayHistory.started_at else None,
                "created_at": h.GameplayHistory.created_at.isoformat() if h.GameplayHistory.created_at else None,
            }
            for h in rows
        ]
    )


# ============ API: Get User Gameplay History (Specific user) ============
@router.get("/gameplay-history/user/{user_id}", response_model=GameplayHistoryResponse)
async def get_user_gameplay_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    level_code: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    game_mode: Optional[str] = Query(None, regex="^(normal|event)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy lịch sử gameplay của user cụ thể
    - Có thể filter theo level_code, ngày, game_mode
    """
    query = select(GameplayHistory).where(GameplayHistory.user_id == user_id)

    # Filters
    if level_code:
        query = query.where(GameplayHistory.level_code == level_code)

    if game_mode:
        query = query.where(GameplayHistory.game_mode == game_mode)

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.where(GameplayHistory.started_at >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format")

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.where(GameplayHistory.started_at <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(GameplayHistory.started_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    histories = result.scalars().all()

    def _safe_json_load(val):
        """Safely load JSON, return None if invalid"""
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(val)
        except Exception:
            return None

    return GameplayHistoryResponse(
        status="success",
        total=total,
        limit=limit,
        offset=offset,
        data=[
            {
                "id": h.id,
                "user_id": h.user_id,
                "msisdn": h.msisdn,
                "level_code": h.level_code,
                "play_attempt": h.play_attempt,
                "score": h.score,
                "coins_earned": h.coins_earned,
                "stars": h.stars,
                "duration_seconds": h.duration_seconds,
                "items_start": _safe_json_load(h.items_start),
                "items_used": _safe_json_load(h.items_used),
                "items_earned": _safe_json_load(h.items_earned),
                "game_mode": h.game_mode,
                "started_at": h.started_at.isoformat() if h.started_at else None,
                "created_at": h.created_at.isoformat() if h.created_at else None
            }
            for h in histories
        ]
    )


# ============ API: Stats theo ngày/tuần/tháng ============
@router.get("/gameplay-stats/{user_id}", response_model=GameplayStatsResponse)
async def get_gameplay_stats(
    user_id: int,
    period: str = Query("daily", regex="^(daily|weekly|monthly|all)$"),
    target_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ Thống kê gameplay: mỗi level chỉ tính điểm cao nhất (tránh spam)
    """
    # --- Xác định khoảng thời gian ---
    if target_date:
        try:
            dt = datetime.fromisoformat(target_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        dt = date.today()

    if period == "daily":
        start_dt = datetime.combine(dt, datetime.min.time())
        end_dt = datetime.combine(dt, datetime.max.time())
    elif period == "weekly":
        start_of_week = dt - timedelta(days=dt.weekday())
        start_dt = datetime.combine(start_of_week, datetime.min.time())
        end_dt = datetime.combine(start_of_week + timedelta(days=6), datetime.max.time())
    elif period == "monthly":
        start_dt = datetime.combine(dt.replace(day=1), datetime.min.time())
        if dt.month == 12:
            end_dt = datetime.combine(date(dt.year + 1, 1, 1) - timedelta(days=1), datetime.max.time())
        else:
            end_dt = datetime.combine(date(dt.year, dt.month + 1, 1) - timedelta(days=1), datetime.max.time())
    else:
        start_dt = datetime.min
        end_dt = datetime.max

    # --- Subquery: lấy điểm cao nhất của từng level ---
    best_score_q = select(
        GameplayHistory.level_code,
        func.max(GameplayHistory.score).label("best_score"),
        func.max(GameplayHistory.coins_earned).label("best_coins"),
        func.max(GameplayHistory.stars).label("best_stars"),
        func.min(GameplayHistory.duration_seconds).label("best_duration")
    ).where(
        and_(
            GameplayHistory.user_id == user_id,
            GameplayHistory.started_at >= start_dt,
            GameplayHistory.started_at <= end_dt
        )
    ).group_by(GameplayHistory.level_code).subquery()

    # --- Tổng hợp ---
    query = select(
        func.count(best_score_q.c.level_code).label('total_games'),
        func.sum(best_score_q.c.best_score).label('total_score'),
        func.sum(best_score_q.c.best_coins).label('total_coins'),
        func.avg(best_score_q.c.best_duration).label('avg_duration')
    )

    result = await db.execute(query)
    row = result.first()

    return GameplayStatsResponse(
        status="success",
        period=period,
        date=dt.isoformat(),
        stats={
            "total_games": int(row.total_games or 0),
            "total_score": int(row.total_score or 0),
            "total_coins": int(row.total_coins or 0),
            "avg_duration_seconds": round(float(row.avg_duration or 0), 2)
        }
    )


# ============ API: Top performers theo level ============
@router.get("/level-leaderboard/{level_code}", response_model=LevelLeaderboardResponse)
async def get_level_leaderboard(
    level_code: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Bảng xếp hạng theo từng màn chơi cụ thể
    """
    def safe_mask_msisdn(msisdn: Optional[str]) -> str:
        if not msisdn or len(msisdn) <= 4:
            return "****"
        return f"{msisdn[:-4]}****"

    # Lấy top scores cho level này
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
    leaders = result.all()

    return LevelLeaderboardResponse(
        status="success",
        level_code=level_code,
        leaderboard=[
            {
                "rank": idx + 1,
                "user_id": row.user_id,
                "display_name": row.display_name,
                "msisdn": safe_mask_msisdn(row.msisdn),
                "best_score": row.best_score,
                "best_stars": row.best_stars,
                "fastest_time_seconds": row.fastest_time
            }
            for idx, row in enumerate(leaders)
        ]
    )