# tasks/leaderboard_etl.py - Updated với win/loss tracking
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, case, cast, Integer
from sqlalchemy.dialects.mysql import insert
from models.models import GameplayHistory, LeaderboardHistory
import logging

logger = logging.getLogger(__name__)
MY_TZ = timezone.utc


def extract_level_number(level_code: str) -> int:
    """Trích xuất số level từ level_code (ví dụ: 'level_038' -> 38)"""
    try:
        if level_code and '_' in level_code:
            return int(level_code.split('_')[-1])
        return 0
    except (ValueError, IndexError):
        return 0


async def snapshot_leaderboard(db: AsyncSession, period: str, target_date: Optional[date] = None):
    """
    Tính toán và lưu leaderboard dựa trên GameplayHistory
    
    Tiêu chí xếp hạng (theo thứ tự ưu tiên):
    1. Tổng điểm (sum(score)) → cao hơn xếp trước
    2. Win rate (win_count/total_games) → cao hơn xếp trước
    3. Số lượt chơi (count) → ít hơn xếp trước
    4. Level cao nhất (max) → cao hơn xếp trước
    5. Mức độ hoàn thành (avg(stars)) → cao hơn xếp trước
    6. Thời gian chơi (sum(duration)) → thấp hơn xếp trước
    7. Thời gian bắt đầu (min(started_at)) → sớm hơn xếp trước
    """
    if target_date is None:
        dt = datetime.now(MY_TZ)
        target_date = dt.date()

    # Xác định khoảng thời gian
    if period == "weekly":
        weekday = target_date.weekday()
        start_date = target_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
        snapshot_date = start_date
    elif period == "monthly":
        start_date = target_date.replace(day=1)
        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
        snapshot_date = start_date
    else:  # daily
        start_date = target_date
        end_date = target_date
        snapshot_date = target_date

    logger.info(f"Snapshot leaderboard period={period} from {start_date} to {end_date}")

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Query aggregate với win/loss tracking
    query = select(
        GameplayHistory.user_id,
        func.sum(GameplayHistory.score).label('total_score'),
        func.count(GameplayHistory.id).label('play_count'),
        func.sum(case((GameplayHistory.result == 0, 1), else_=0)).label('win_count'),
        func.sum(case((GameplayHistory.result == 1, 1), else_=0)).label('loss_count'),
        # func.max(
        #     case(
        #         (GameplayHistory.level_code.like('level_%'),
        #          cast(func.substring_index(GameplayHistory.level_code, '_', -1), Integer)),
        #         else_=0
        #     )
        # ).label('max_level'),
        func.avg(GameplayHistory.stars).label('avg_stars'),
        func.sum(GameplayHistory.duration_seconds).label('total_duration'),
        func.min(GameplayHistory.started_at).label('first_played_at'),
        func.sum(GameplayHistory.coins_earned).label('total_coins'),
        func.count(func.distinct(GameplayHistory.level_code)).label('level_played')
    ).where(
        and_(
            GameplayHistory.started_at >= start_dt,
            GameplayHistory.started_at <= end_dt
        )
    ).group_by(GameplayHistory.user_id)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        logger.info("No gameplay data found for this period, skipping snapshot")
        return 0

    # Chuyển đổi sang list of dict và tính win_rate
    players = []
    for row in rows:
        play_count = int(row.play_count or 0)
        win_count = int(row.win_count or 0)
        win_rate = (win_count / play_count * 100) if play_count > 0 else 0.0
        
        players.append({
            'user_id': row.user_id,
            'total_score': int(row.total_score or 0),
            'play_count': play_count,
            'win_count': win_count,
            'loss_count': int(row.loss_count or 0),
            'win_rate': win_rate,
            'max_level': int(row.max_level or 0),
            'avg_stars': float(row.avg_stars or 0),
            'total_duration': int(row.total_duration or 0),
            'first_played_at': row.first_played_at,
            'total_coins': int(row.total_coins or 0),
            'level_played': int(row.level_played or 0)
        })

    # Sắp xếp theo 7 tiêu chí
    sorted_players = sorted(players, key=lambda p: (
        -p['total_score'],          # 1. Điểm cao hơn → trước
        -p['win_rate'],             # 2. Win rate cao hơn → trước
        p['play_count'],            # 3. Ít lượt chơi hơn → trước
        -p['max_level'],            # 4. Level cao hơn → trước
        -p['avg_stars'],            # 5. Sao nhiều hơn → trước
        p['total_duration'],        # 6. Thời gian ít hơn → trước
        p['first_played_at'] if p['first_played_at'] else datetime.max  # 7. Chơi sớm hơn → trước
    ))

    # Gán thứ hạng và chuẩn bị insert
    inserts = []
    for rank, player in enumerate(sorted_players, start=1):
        inserts.append({
            "user_id": player['user_id'],
            "date": snapshot_date,
            "period": period,
            "scores": player['total_score'],
            "play_count": player['play_count'],
            "win_count": player['win_count'],
            "loss_count": player['loss_count'],
            "win_rate": player['win_rate'],
            "max_level": player['max_level'],
            "avg_stars": player['avg_stars'],
            "total_duration": player['total_duration'],
            "first_played_at": player['first_played_at'],
            "rank": rank,
            "coins": player['total_coins'],
            "level_played": player['level_played']
        })

    # Use ON DUPLICATE KEY UPDATE (MySQL / MariaDB)
    stmt = insert(LeaderboardHistory).values(inserts)
    stmt = stmt.on_duplicate_key_update(
        scores=stmt.inserted.scores,
        play_count=stmt.inserted.play_count,
        win_count=stmt.inserted.win_count,
        loss_count=stmt.inserted.loss_count,
        win_rate=stmt.inserted.win_rate,
        max_level=stmt.inserted.max_level,
        avg_stars=stmt.inserted.avg_stars,
        total_duration=stmt.inserted.total_duration,
        first_played_at=stmt.inserted.first_played_at,
        rank=stmt.inserted.rank,
        coins=stmt.inserted.coins,
        level_played=stmt.inserted.level_played
    )

    await db.execute(stmt)
    await db.commit()

    logger.info(f"✅ Inserted/Updated {len(inserts)} leaderboard rows for period={period} date={snapshot_date}")
    
    # Log top 3 players with win rate
    if len(inserts) >= 3:
        top3_info = [
            f"#{p['rank']}:user_{p['user_id']}({p['total_score']}pts, {p['win_rate']:.1f}%WR)" 
            for p in inserts[:3]
        ]
        logger.info(f"   Top 3: {', '.join(top3_info)}")
    
    return len(inserts)


async def snapshot_daily(db: AsyncSession, target_date: Optional[date] = None):
    """Snapshot leaderboard hàng ngày"""
    return await snapshot_leaderboard(db, "daily", target_date)


async def snapshot_weekly(db: AsyncSession, target_date: Optional[date] = None):
    """Snapshot leaderboard hàng tuần"""
    return await snapshot_leaderboard(db, "weekly", target_date)


async def snapshot_monthly(db: AsyncSession, target_date: Optional[date] = None):
    """Snapshot leaderboard hàng tháng"""
    return await snapshot_leaderboard(db, "monthly", target_date)


async def backfill_leaderboard(
    db: AsyncSession, 
    start_date: date, 
    end_date: date,
    periods: list = ["daily", "weekly", "monthly"]
):
    """
    Tính lại leaderboard cho nhiều ngày
    Warning: Có thể mất nhiều thời gian với range lớn
    """
    current_date = start_date
    total_processed = 0

    while current_date <= end_date:
        logger.info(f"📅 Backfilling leaderboard for {current_date}")

        for period in periods:
            try:
                count = await snapshot_leaderboard(db, period, current_date)
                total_processed += count
                logger.info(f"   ✓ {period}: {count} records")
            except Exception as e:
                logger.error(f"   ✗ Error backfilling {period} for {current_date}: {str(e)}")

        current_date += timedelta(days=1)

    logger.info(f"🎉 Backfill completed. Total records: {total_processed}")
    return total_processed