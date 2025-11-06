# main.py - Updated with Gameplay History API
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import (
    status, statement, spin, leaderboard, shop, myid_web_charge,
    gameplay_history, admin_leaderboard, terms_and_conditions  # NEW: Gameplay history router
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta, timezone
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from tasks.leaderboard_etl import snapshot_leaderboard
from logging_config import setup_logging
import logging
import traceback
from scheduler_setup import start_scheduler, shutdown_scheduler

# Setup comprehensive logging
log_file = setup_logging()
logger = logging.getLogger(__name__)

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

app = FastAPI(
    title="Hero Saga API",
    description="Game API with MyID Integration + Shop + Dashboard + Gameplay History",
    version="2.4.0"  # Updated version
)

# ====== CORS middleware ======
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Middleware to log all requests ======
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    
    # Log request
    logger.info(f"REQUEST: {request.method} {request.url}")
    logger.info(f"Client IP: {request.client.host if request.client else 'unknown'}")
    
    # Log headers (mask sensitive data)
    headers_to_log = {}
    for k, v in request.headers.items():
        if k.lower() in ['authorization', 'access-token', 'auth']:
            headers_to_log[k] = f"{v[:10]}...***" if len(v) > 10 else "***"
        else:
            headers_to_log[k] = v
    logger.info(f"Headers: {headers_to_log}")
    
    try:
        response = await call_next(request)
        
        # Log response
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"RESPONSE: {response.status_code} - {process_time:.3f}s")
        
        return response
    except Exception as e:
        # Log errors
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"ERROR in request {request.method} {request.url}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Process time: {process_time:.3f}s")
        raise

# ====== Include API routers ======
app.include_router(status.router, prefix="/herosaga")
app.include_router(statement.router, prefix="/herosaga")
app.include_router(spin.router, prefix="/herosaga")
app.include_router(leaderboard.router, prefix="/herosaga")
app.include_router(shop.router, prefix="/herosaga")
app.include_router(gameplay_history.router, prefix="/herosaga")  # NEW
app.include_router(myid_web_charge.router, prefix="/api/myid")
app.include_router(admin_leaderboard.router, prefix="/herosaga", tags=["admin"])
app.include_router(terms_and_conditions.router, prefix="/herosaga")

# ====== Health check ======
@app.get("/api/health")
def health_check():
    logger.info("Health check requested")
    return {
        "status": "healthy", 
        "services": ["game", "myid", "shop", "dashboard", "gameplay", "revenue"],
        "version": "2.4.0"
    }

@app.get("/api/server-timestamp")
def server_timestamp():
    now = datetime.now(MYANMAR_TZ)
    logger.info(f"Server timestamp requested: {now.isoformat()}")
    return {
        "timestamp": int(now.timestamp()),
        "datetime": now.isoformat()
    }

# ====== Scheduler setup ======
scheduler = AsyncIOScheduler(timezone=MYANMAR_TZ)

async def snapshot_job(period: str):
    logger.info(f"Starting {period} snapshot job")
    try:
        async for db in get_db():
            await snapshot_leaderboard(db, period)
        logger.info(f"Completed {period} snapshot job successfully")
    except Exception as e:
        logger.error(f"Error in {period} snapshot job: {str(e)}")
        logger.error(traceback.format_exc())

# Daily snapshot: 00:05 Myanmar time
scheduler.add_job(snapshot_job, CronTrigger(hour=0, minute=5), args=["daily"])

# Weekly snapshot: Monday 00:10 Myanmar time
scheduler.add_job(snapshot_job, CronTrigger(day_of_week="mon", hour=0, minute=10), args=["weekly"])

# Monthly snapshot: Day 1 00:20 Myanmar time
scheduler.add_job(snapshot_job, CronTrigger(day=1, hour=0, minute=20), args=["monthly"])

@app.on_event("startup")
async def startup_event():
    logger.info("="*50)
    logger.info("APPLICATION STARTUP")
    logger.info("="*50)
    logger.info(f"Log file: {log_file}")
    logger.info(f"Startup time: {datetime.now(MYANMAR_TZ).isoformat()}")
    logger.info(f"Python version: {__import__('sys').version}")
    logger.info(f"FastAPI running on port 8113")
    
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
        logger.info("Scheduled jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - {job.id}: {job.next_run_time}")
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        logger.error(traceback.format_exc())
    
    logger.info("="*50)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("="*50)
    logger.info("APPLICATION SHUTDOWN")
    logger.info("="*50)
    logger.info(f"Shutdown time: {datetime.now(MYANMAR_TZ).isoformat()}")
    
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
    
    logger.info("Application shutdown complete")
    logger.info("="*50)
    
@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    shutdown_scheduler()