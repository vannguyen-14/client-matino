from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis
import json
import asyncio
from datetime import datetime

from models.models import User, GameStatement, GameStatementSummary
from database import get_db
import config_sys
from fastapi.responses import JSONResponse
from utils.auth_helper import get_user_from_auth

# =============================
# Redis setup
# =============================
redis: Redis | None = None

async def ensure_redis():
    global redis
    if redis is None:
        redis = Redis(
            host=config_sys.REDIS_HOST,
            port=config_sys.REDIS_PORT,
            db=config_sys.REDIS_DB,
            decode_responses=True
        )
    return redis

router = APIRouter()

# -----------------------------
# Helpers
# -----------------------------
async def get_user_by_token(db: AsyncSession, user_id: int, token: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.api_token == token))
    return result.scalars().first()

async def get_latest_statement(db: AsyncSession, user_id: int) -> GameStatement | None:
    result = await db.execute(
        select(GameStatement)
        .where(GameStatement.user_id == user_id)
        .order_by(GameStatement.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()

def compute_achie_count(data: dict) -> int:
    return sum(
        1 for k, v in data.items()
        if k.startswith("achie") and not k.startswith("achieLv")
        and isinstance(v, (int, float)) and v > 0
    )

async def upsert_statement_and_summary(
    db: AsyncSession,
    user_id: int,
    merged_data: dict,
    existing_stmt: GameStatement | None
) -> int:
    """Insert if no statement; otherwise update JSON + summary. Returns statement_id."""
    if existing_stmt is None:
        stmt = GameStatement(
            user_id=user_id,
            session_id=None,
            file_name=None,
            payload_version=1,
            statement_json=json.dumps(merged_data)
        )
        db.add(stmt)
        await db.flush()
        stmt_id = stmt.id

        summary = GameStatementSummary(
            user_id=user_id,
            statement_id=stmt_id,
            coins=merged_data.get("coins", 0),
            scores=merged_data.get("scores", 0),
            level_played=merged_data.get("levelPlayed", 0),
            language_id=merged_data.get("languageId"),
            last_login_time=merged_data.get("lastLoginTime"),
            daily_day=merged_data.get("dailyDay"),
            skin_equipped=merged_data.get("skinEquiped"),
            achie_count=compute_achie_count(merged_data)
        )
        db.add(summary)
    else:
        try:
            current_data = json.loads(existing_stmt.statement_json) if existing_stmt.statement_json else {}
        except json.JSONDecodeError:
            current_data = {}
        current_data.update(merged_data)
        existing_stmt.statement_json = json.dumps(current_data)

        result = await db.execute(select(GameStatementSummary).where(GameStatementSummary.statement_id == existing_stmt.id))
        summary = result.scalars().first()
        if summary:
            summary.coins = current_data.get("coins", summary.coins)
            summary.scores = current_data.get("scores", summary.scores)
            summary.level_played = current_data.get("levelPlayed", summary.level_played)
            summary.language_id = current_data.get("languageId", summary.language_id)
            summary.last_login_time = current_data.get("lastLoginTime", summary.last_login_time)
            summary.daily_day = current_data.get("dailyDay", summary.daily_day)
            summary.skin_equipped = current_data.get("skinEquiped", summary.skin_equipped)
            summary.achie_count = compute_achie_count(current_data)
        else:
            summary = GameStatementSummary(
                user_id=user_id,
                statement_id=existing_stmt.id,
                coins=current_data.get("coins", 0),
                scores=current_data.get("scores", 0),
                level_played=current_data.get("levelPlayed", 0),
                language_id=current_data.get("languageId"),
                last_login_time=current_data.get("lastLoginTime"),
                daily_day=current_data.get("dailyDay"),
                skin_equipped=current_data.get("skinEquiped"),
                achie_count=compute_achie_count(current_data)
            )
            db.add(summary)
        stmt_id = existing_stmt.id

    await db.commit()
    return stmt_id

# -----------------------------
# Redis key helpers
# -----------------------------
def rt_key(user_id: int) -> str:
    return f"gs:{user_id}"

# =============================
# API: realtime update -> Redis
# =============================
@router.post("/rt-update-game-statement")
async def rt_update_game_statement(payload: dict, db: AsyncSession = Depends(get_db)):
    auth = payload.get("auth")
    patch = payload.get("patch")
    if not auth or not isinstance(patch, dict):
        raise HTTPException(status_code=400, detail="Missing required fields")

    user = await get_user_from_auth(auth, db)
    if isinstance(user, JSONResponse):  # nếu lỗi thì return luôn
        return user

    user_id = user.id

    r = await ensure_redis()
    key = rt_key(user_id)

    raw = await r.hget(key, "data")
    if raw is None:
        stmt = await get_latest_statement(db, user_id)
        base = {}
        if stmt and stmt.statement_json:
            try:
                base = json.loads(stmt.statement_json)
            except json.JSONDecodeError:
                base = {}
    else:
        try:
            base = json.loads(raw)
        except json.JSONDecodeError:
            base = {}

    base.update(patch)

    pipe = r.pipeline()
    pipe.hset(key, mapping={
        "data": json.dumps(base),
        "updated_at": datetime.utcnow().isoformat()
    })
    pipe.hincrby(key, "version", 1)
    await pipe.execute()

    version = int(await r.hget(key, "version") or 0)
    return {"status": "success", "message": "realtime updated", "version": version}

# =============================
# API: save (finalize)
# =============================
@router.post("/save-game-statement")
async def save_game_statement(payload: dict, db: AsyncSession = Depends(get_db)):
    user_id = payload.get("user_id")
    token = payload.get("token")
    json_data = payload.get("json_data")

    if not user_id or not token:
        raise HTTPException(status_code=400, detail="Missing required fields")

    user = await get_user_by_token(db, user_id, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user or token")

    r = await ensure_redis()
    key = rt_key(user_id)

    raw = await r.hget(key, "data")
    data: dict
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = json_data or {}
    else:
        if not isinstance(json_data, dict):
            stmt = await get_latest_statement(db, user_id)
            if not stmt:
                raise HTTPException(status_code=400, detail="No Redis state. Provide json_data for first-time save.")
            try:
                data = json.loads(stmt.statement_json or "{}")
            except json.JSONDecodeError:
                data = {}
        else:
            data = json_data

    existing_stmt = await get_latest_statement(db, user_id)
    stmt_id = await upsert_statement_and_summary(db, user_id, data, existing_stmt)

    await r.hset(key, mapping={"last_flush_version": await r.hget(key, "version") or 0})

    return {"status": "success", "message": "Game statement saved", "statement_id": stmt_id}

# =============================
# API: get
# =============================
@router.get("/get-game-statement/{user_id}")
async def get_game_statement(user_id: int, db: AsyncSession = Depends(get_db)):
    r = await ensure_redis()
    key = rt_key(user_id)
    raw = await r.hget(key, "data")
    if raw:
        try:
            data = json.loads(raw)
            source = "redis"
        except json.JSONDecodeError:
            data = None
            source = "redis-invalid"
    else:
        data = None
        source = "db"

    if data is None:
        stmt = await get_latest_statement(db, user_id)
        if not stmt:
            raise HTTPException(status_code=404, detail="No statements found for this user")
        try:
            data = json.loads(stmt.statement_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid JSON data stored")
        return {"status": "success", "source": source, "statement_id": stmt.id, "user_id": stmt.user_id, "json_data": data}

    return {"status": "success", "source": source, "statement_id": None, "user_id": user_id, "json_data": data}

# =============================
# Admin flush
# =============================
@router.post("/admin/flush-realtime/{user_id}")
async def admin_flush_realtime(user_id: int, db: AsyncSession = Depends(get_db)):
    r = await ensure_redis()
    key = rt_key(user_id)
    raw = await r.hget(key, "data")
    if not raw:
        raise HTTPException(status_code=404, detail="No realtime state in Redis")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Bad JSON in Redis")

    existing_stmt = await get_latest_statement(db, user_id)
    stmt_id = await upsert_statement_and_summary(db, user_id, data, existing_stmt)
    await r.hset(key, mapping={"last_flush_version": await r.hget(key, "version") or 0})
    return {"status": "success", "statement_id": stmt_id}

# =============================
# Startup
# =============================
@router.on_event("startup")
async def _on_startup():
    await ensure_redis()
