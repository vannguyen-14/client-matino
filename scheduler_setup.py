# scheduler_setup.py - Cấu hình APScheduler cho leaderboard ETL
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
from database import AsyncSessionLocal
from tasks.leaderboard_etl import snapshot_daily, snapshot_weekly, snapshot_monthly
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# Myanmar timezone offset: UTC+6:30
# Để chuyển từ Myanmar time sang UTC, trừ đi 6h30
# Myanmar 23:45 = UTC 17:15
# Myanmar 23:50 = UTC 17:20
# Myanmar 23:55 = UTC 17:25

async def snapshot_job(period: str):
    """
    Wrapper job để chạy snapshot với async session
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"🚀 Starting {period} leaderboard snapshot...")
            start_time = datetime.now(timezone.utc)
            
            if period == "daily":
                count = await snapshot_daily(db)
            elif period == "weekly":
                count = await snapshot_weekly(db)
            elif period == "monthly":
                count = await snapshot_monthly(db)
            else:
                logger.error(f"Unknown period: {period}")
                return
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"✅ {period.capitalize()} snapshot completed in {elapsed:.2f}s, processed {count} records")
            
        except Exception as e:
            logger.error(f"❌ Error in {period} snapshot: {str(e)}", exc_info=True)
        finally:
            await db.close()

def setup_leaderboard_scheduler():
    """
    Thiết lập lịch chạy ETL cho leaderboard
    Chạy vào khung giờ ít người chơi (23:45-23:59 Myanmar time)
    """
    
    # Daily snapshot: 23:45 Myanmar time = 17:15 UTC
    scheduler.add_job(
        snapshot_job,
        CronTrigger(hour=17, minute=15, timezone='UTC'),
        args=["daily"],
        id="daily_snapshot",
        name="Daily Leaderboard Snapshot",
        replace_existing=True
    )
    logger.info("📅 Scheduled daily leaderboard snapshot at 23:45 Myanmar time (17:15 UTC)")
    
    # Weekly snapshot: Sunday 23:50 Myanmar time = Sunday 17:20 UTC
    scheduler.add_job(
        snapshot_job,
        CronTrigger(day_of_week='sun', hour=17, minute=20, timezone='UTC'),
        args=["weekly"],
        id="weekly_snapshot",
        name="Weekly Leaderboard Snapshot",
        replace_existing=True
    )
    logger.info("📅 Scheduled weekly leaderboard snapshot at Sunday 23:50 Myanmar time (17:20 UTC)")
    
    # Monthly snapshot: Last day of month 23:55 Myanmar time = 17:25 UTC
    scheduler.add_job(
        snapshot_job,
        CronTrigger(day='last', hour=17, minute=25, timezone='UTC'),
        args=["monthly"],
        id="monthly_snapshot",
        name="Monthly Leaderboard Snapshot",
        replace_existing=True
    )
    logger.info("📅 Scheduled monthly leaderboard snapshot at last day 23:55 Myanmar time (17:25 UTC)")

def start_scheduler():
    """Khởi động scheduler"""
    setup_leaderboard_scheduler()
    scheduler.start()
    logger.info("⏰ APScheduler started successfully")

def shutdown_scheduler():
    """Dừng scheduler"""
    scheduler.shutdown()
    logger.info("⏰ APScheduler shut down")