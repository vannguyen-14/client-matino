# routers/leaderboard.py - Enhanced với logic xếp hạng 6 tiêu chí
import json
from sqlalchemy import desc, func, and_, select as sa_select, case, cast, Integer
from sqlalchemy.future import select
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone, date
from models.models import LeaderboardHistory, GameplayHistory, User, GameStatement
from database import get_db
from utils.auth_helper import get_user_from_auth
from fastapi.responses import JSONResponse
from typing import Optional, List

router = APIRouter()
UTC = timezone.utc

def mask_msisdn(msisdn: str) -> str:
    """Ẩn số điện thoại: giữ 3 số đầu và 3 số cuối nếu đủ dài"""
    if not msisdn or len(msisdn) <= 6:
        return "****"
    return f"{msisdn[:3]}***{msisdn[-3:]}"

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

# ============ API: Realtime Leaderboard với logic 6 tiêu chí ============
@router.get("/leaderboard/realtime")
async def get_realtime_leaderboard(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    date_str: str = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(10, ge=1, le=200),
    auth: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Leaderboard REALTIME - tính trực tiếp từ GameplayHistory
    ✅ Logic mới:
        - Chỉ cộng điểm cao nhất mỗi level cho mỗi user (tránh spam level)
        - Tổng hợp theo 6 tiêu chí: điểm, số lần chơi, level cao nhất, sao trung bình, thời lượng, v.v.
    """
    # --- Xác định target date ---
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now(UTC).date()

    # --- Khoảng thời gian ---
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

    # --- Subquery 1: lấy điểm cao nhất của từng level cho mỗi user ---
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

    # --- Subquery 2: tổng hợp lại theo user ---
    agg_q = sa_select(
        best_score_q.c.user_id,
        func.sum(best_score_q.c.best_score).label("total_scores"),
        func.count(best_score_q.c.level_code).label("games_played"),
        func.max(best_score_q.c.level_code).label("max_level"),
        func.avg(best_score_q.c.best_stars).label("avg_stars"),
        func.sum(best_score_q.c.best_duration).label("total_duration")
    ).group_by(best_score_q.c.user_id).subquery()

    # --- Join với User và GameStatement ---
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

    # --- Sắp xếp theo tiêu chí ---
    sorted_players = sorted(players, key=lambda p: (
        -(p.total_scores or 0),
        -(p.games_played or 0),
        -(p.avg_stars or 0),
        (p.total_duration or 0)
    ))

    # --- Giới hạn top ---
    top_players = sorted_players[:limit]

    # --- Tính rank của user hiện tại (nếu có auth) ---
    your_rank = None
    your_stats = None
    if auth:
        user = await get_user_from_auth(auth, db)
        if isinstance(user, JSONResponse):
            return user
        user_id = user.id
        for idx, p in enumerate(sorted_players, start=1):
            if p.user_id == user_id:
                your_rank = idx
                your_stats = {
                    "total_scores": int(p.total_scores or 0),
                    "games_played": int(p.games_played or 0),
                    "avg_stars": round(float(p.avg_stars or 0), 2),
                    "total_duration": int(p.total_duration or 0)
                }
                break

    # --- Kết quả ---
    leaderboard = [
        {
            "rank": idx + 1,
            "user_id": row.user_id,
            "name": extract_name(row.statement_json),
            "avatar": extract_avatar(row.statement_json),
            "msisdn": mask_msisdn(row.msisdn),
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
        "source": "realtime_best_per_level",
        "leaderboard": leaderboard,
        "your_rank": your_rank,
        "your_stats": your_stats
    }


# ============ API: Cached Leaderboard với rank đã tính sẵn ============
@router.get("/leaderboard")
async def get_leaderboard(
    period: str = Query("all", regex="^(all|daily|weekly|monthly)$"),
    date_str: str = Query(None, description="YYYY-MM-DD (default today for daily/weekly/monthly)"),
    limit: int = Query(10, ge=1, le=200),
    auth: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ Leaderboard chính:
    - `all`      → realtime từ GameplayHistory, tính best score mỗi level
    - `daily`    → snapshot LeaderboardHistory
    - `weekly`   → snapshot LeaderboardHistory
    - `monthly`  → snapshot LeaderboardHistory
    """

    # ---------------------- CASE 1: ALL-TIME ----------------------
    if period == "all":
        # --- Subquery 1: best score per level per user ---
        best_score_q = sa_select(
            GameplayHistory.user_id.label("user_id"),
            GameplayHistory.level_code.label("level_code"),
            func.max(GameplayHistory.score).label("best_score"),
            func.max(GameplayHistory.stars).label("best_stars"),
            func.min(GameplayHistory.duration_seconds).label("best_duration")
        ).where(
            GameplayHistory.game_mode == 'normal'
        ).group_by(GameplayHistory.user_id, GameplayHistory.level_code).subquery()

        # --- Subquery 2: tổng hợp theo user ---
        agg_q = sa_select(
            best_score_q.c.user_id,
            func.sum(best_score_q.c.best_score).label("total_scores"),
            func.count(best_score_q.c.level_code).label("games_played"),
            func.max(best_score_q.c.level_code).label("max_level"),  # ✅ thêm max_level
            func.avg(best_score_q.c.best_stars).label("avg_stars"),
            func.sum(best_score_q.c.best_duration).label("total_duration")
        ).group_by(best_score_q.c.user_id).subquery()

        # --- Join với User và GameStatement ---
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

        # --- Sắp xếp ---
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
                "msisdn": mask_msisdn(row.msisdn),
                "scores": int(row.total_scores or 0),
                "games_played": int(row.games_played or 0),
                "max_level": row.max_level or 0,
                "avg_stars": round(float(row.avg_stars or 0), 2),
                "total_duration": int(row.total_duration or 0)
            }
            for idx, row in enumerate(top_players)
        ]

        # --- Tính your_rank nếu có auth ---
        your_rank = None
        your_stats = None
        if auth:
            user = await get_user_from_auth(auth, db)
            if isinstance(user, JSONResponse):
                return user
            user_id = user.id

            for idx, row in enumerate(sorted_players):
                if row.user_id == user_id:
                    your_rank = idx + 1
                    your_stats = {
                        "scores": int(row.total_scores or 0),
                        "games_played": int(row.games_played or 0),
                        "max_level": row.max_level or 0,
                        "avg_stars": round(float(row.avg_stars or 0), 2),
                        "total_duration": int(row.total_duration or 0)
                    }
                    break

        return {
            "status": "success",
            "period": "all",
            "source": "all_time_best_per_level",
            "leaderboard": leaderboard,
            "your_rank": your_rank,
            "your_stats": your_stats
        }

    # ---------------------- CASE 2: DAILY / WEEKLY / MONTHLY ----------------------
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now(UTC).date()

    q = sa_select(
        LeaderboardHistory.user_id,
        LeaderboardHistory.rank,
        LeaderboardHistory.scores,
        LeaderboardHistory.coins,
        LeaderboardHistory.level_played,
        LeaderboardHistory.play_count,
        LeaderboardHistory.max_level,
        LeaderboardHistory.avg_stars,
        LeaderboardHistory.total_duration,
        GameStatement.statement_json,
        User.msisdn
    ).join(User, User.id == LeaderboardHistory.user_id)\
     .outerjoin(GameStatement, GameStatement.user_id == LeaderboardHistory.user_id)\
     .where(
        LeaderboardHistory.period == period,
        LeaderboardHistory.date == target_date
    ).order_by(LeaderboardHistory.rank).limit(limit)

    res = await db.execute(q)
    players = res.all()

    leaderboard = [
        {
            "rank": row.rank,
            "user_id": row.user_id,
            "name": extract_name(row.statement_json),
            "avatar": extract_avatar(row.statement_json),
            "msisdn": mask_msisdn(row.msisdn),
            "coins": row.coins,
            "scores": row.scores,
            "level_played": row.level_played,
            "play_count": row.play_count,
            "max_level": row.max_level or 0,
            "avg_stars": round(float(row.avg_stars or 0), 2),
            "total_duration": row.total_duration
        }
        for row in players
    ]

    # --- Tính your_rank nếu có auth ---
    your_rank = None
    your_stats = None
    if auth:
        user = await get_user_from_auth(auth, db)
        if isinstance(user, JSONResponse):
            return user
        user_id = user.id

        rank_q = sa_select(LeaderboardHistory.rank).where(
            LeaderboardHistory.user_id == user_id,
            LeaderboardHistory.period == period,
            LeaderboardHistory.date == target_date
        )
        rank_res = await db.execute(rank_q)
        your_rank = rank_res.scalar()

    return {
        "status": "success",
        "period": period,
        "date": str(target_date),
        "source": "snapshot_best_per_level",
        "leaderboard": leaderboard,
        "your_rank": your_rank,
        "your_stats": your_stats
    }


# ============ API: Get User Rank Details ============
@router.get("/leaderboard/my-rank")
async def get_my_rank(
    period: str = Query("daily", regex="^(daily|weekly|monthly|all)$"),
    date: str = Query(None, description="YYYY-MM-DD"),
    auth: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy thông tin chi tiết về rank của user hiện tại
    """
    user = await get_user_from_auth(auth, db)
    if isinstance(user, JSONResponse):
        return user

    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    elif period != "all":
        target_date = datetime.now(UTC).date()

    if period == "all":
        return {"status": "error", "message": "Use /leaderboard?period=all with auth for all-time rank"}

    # Lấy thông tin từ LeaderboardHistory
    q = sa_select(
        LeaderboardHistory.rank,
        LeaderboardHistory.scores,
        LeaderboardHistory.play_count,
        LeaderboardHistory.max_level,
        LeaderboardHistory.avg_stars,
        LeaderboardHistory.total_duration,
        LeaderboardHistory.first_played_at,
        LeaderboardHistory.coins,
        LeaderboardHistory.level_played
    ).where(
        LeaderboardHistory.user_id == user.id,
        LeaderboardHistory.period == period,
        LeaderboardHistory.date == target_date
    )

    res = await db.execute(q)
    row = res.first()

    if not row:
        return {
            "status": "success",
            "period": period,
            "date": str(target_date),
            "rank": None,
            "message": "No gameplay data for this period"
        }

    return {
        "status": "success",
        "period": period,
        "date": str(target_date),
        "rank": row.rank,
        "stats": {
            "scores": row.scores,
            "play_count": row.play_count,
            "max_level": row.max_level,
            "avg_stars": round(float(row.avg_stars or 0), 2),
            "total_duration": row.total_duration,
            "first_played_at": row.first_played_at.isoformat() if row.first_played_at else None,
            "coins": row.coins,
            "level_played": row.level_played
        }
    }