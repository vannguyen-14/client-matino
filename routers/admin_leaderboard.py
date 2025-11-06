# routers/admin_leaderboard.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, select as sa_select, case, cast, Integer
from datetime import datetime, date, timedelta
from database import get_db
from tasks.leaderboard_etl import snapshot_leaderboard, backfill_leaderboard
from models.models import GameplayHistory, User, GameStatement
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_name(statement_json: str) -> str:
    """Lấy name từ statement_json"""
    try:
        data = json.loads(statement_json) if isinstance(statement_json, str) else (statement_json or {})
        return data.get("name", "Player")
    except Exception:
        return "Player"

def extract_avatar(statement_json: str) -> int:
    """Lấy avatar từ statement_json"""
    try:
        data = json.loads(statement_json) if isinstance(statement_json, str) else (statement_json or {})
        return data.get("avatar", 0)
    except Exception:
        return 0

@router.post("/admin/leaderboard/snapshot")
async def admin_snapshot_leaderboard(
    period: str = Query(..., regex="^(daily|weekly|monthly)$"),
    date_str: str = Query(None, description="YYYY-MM-DD, default today"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger leaderboard snapshot
    Cần có admin authentication trong production
    """
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()
    
    try:
        count = await snapshot_leaderboard(db, period, target_date)
        return {
            "status": "success",
            "message": f"Snapshot completed for {period}",
            "date": str(target_date),
            "records_processed": count
        }
    except Exception as e:
        logger.error(f"Error in snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/leaderboard/backfill")
async def admin_backfill_leaderboard(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    periods: str = Query("daily,weekly,monthly", description="Comma-separated: daily,weekly,monthly"),
    db: AsyncSession = Depends(get_db)
):
    """
    Backfill leaderboard data for a date range
    Warning: Có thể mất nhiều thời gian với range lớn
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    period_list = [p.strip() for p in periods.split(",")]
    
    try:
        total = await backfill_leaderboard(db, start, end, period_list)
        return {
            "status": "success",
            "message": "Backfill completed",
            "start_date": str(start),
            "end_date": str(end),
            "periods": period_list,
            "total_records": total
        }
    except Exception as e:
        logger.error(f"Error in backfill: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/leaderboard/full")
async def get_admin_full_leaderboard(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    date_str: str = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin endpoint - BXH với full MSISDN, chỉ tính điểm cao nhất mỗi level
    ⚠️ Dành riêng cho CMS hiển thị leaderboard tổng hợp chính xác
    """
    # Xác định ngày
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now().date()

    # Khoảng thời gian
    if period == "weekly":
        weekday = target_date.weekday()
        start_date = target_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
    elif period == "monthly":
        start_date = target_date.replace(day=1)
        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
    else:
        start_date = target_date
        end_date = target_date

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # --- Subquery 1: best score per level per user ---
    best_score_q = sa_select(
        GameplayHistory.user_id.label("user_id"),
        GameplayHistory.level_code.label("level_code"),
        func.max(GameplayHistory.score).label("best_score"),
        func.max(GameplayHistory.stars).label("best_stars"),
        func.min(GameplayHistory.duration_seconds).label("best_duration")
    ).where(
        and_(
            GameplayHistory.started_at >= start_dt,
            GameplayHistory.started_at <= end_dt,
            GameplayHistory.game_mode == 'normal'
        )
    ).group_by(GameplayHistory.user_id, GameplayHistory.level_code).subquery()

    # --- Subquery 2: aggregate by user ---
    agg_q = sa_select(
        best_score_q.c.user_id,
        func.sum(best_score_q.c.best_score).label("total_scores"),
        func.count(best_score_q.c.level_code).label("games_played"),
        func.max(
            case(
                (best_score_q.c.level_code.like('level_%'),
                cast(func.substring_index(best_score_q.c.level_code, '_', -1), Integer)),
                else_=0
            )
        ).label("max_level"),
        func.avg(best_score_q.c.best_stars).label("avg_stars"),
        func.sum(best_score_q.c.best_duration).label("total_duration")
    ).group_by(best_score_q.c.user_id).subquery()


    # Join với User và GameStatement
    q = sa_select(
        agg_q.c.user_id,
        agg_q.c.total_scores,
        agg_q.c.games_played,
        agg_q.c.max_level,  
        agg_q.c.avg_stars,
        agg_q.c.total_duration,
        GameStatement.statement_json,
        User.msisdn
    ).join(User, User.id == agg_q.c.user_id)\
     .outerjoin(GameStatement, GameStatement.user_id == agg_q.c.user_id)

    res = await db.execute(q)
    players = res.all()

    # Sắp xếp
    sorted_players = sorted(players, key=lambda p: (
        -(p.total_scores or 0),
        -(p.games_played or 0),
        -(p.avg_stars or 0),
        (p.total_duration or 0)
    ))

    top_players = sorted_players[:limit]

    leaderboard = [
        {
            "rank": idx + 1,
            "user_id": row.user_id,
            "name": extract_name(row.statement_json),
            "avatar": extract_avatar(row.statement_json),
            "msisdn": row.msisdn,
            "scores": int(row.total_scores or 0),
            "games_played": int(row.games_played or 0),
            "max_level": row.max_level or 0,
            "avg_stars": round(float(row.avg_stars or 0), 2),
            "total_duration": int(row.total_duration or 0)
        }
        for idx, row in enumerate(top_players)
    ]

    return {
        "status": "success",
        "period": period,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "source": "admin_full_best_per_level",
        "leaderboard": leaderboard
    }