import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone

from models.models import User, GameStatementSummary, SpinReward
from database import get_db
from typing import List
from pydantic import BaseModel

router = APIRouter()
MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

class SpinRewardPartialUpdate(BaseModel):
    id: int
    codename: str | None = None
    amount: int | None = None
    weight: int | None = None
    position: int | None = None

@router.post("/spin")
async def spin(payload: dict, db: AsyncSession = Depends(get_db)):
    user_id = payload.get("user_id")
    token = payload.get("token")

    if not user_id or not token:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # 1. Xác thực user
    result = await db.execute(
        select(User).where(User.id == user_id, User.api_token == token)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user or token")

    # 2. Lấy summary
    result = await db.execute(
        select(GameStatementSummary).where(GameStatementSummary.user_id == user_id)
    )
    summary = result.scalars().first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # 3. Kiểm tra lượt quay
    spin_left = summary.spin_count or 0
    if spin_left <= 0:
        raise HTTPException(status_code=403, detail="No spins left for today")

    # 4. Lấy danh sách phần thưởng
    result = await db.execute(select(SpinReward).order_by(SpinReward.position))
    rewards = result.scalars().all()
    if not rewards:
        raise HTTPException(status_code=500, detail="No rewards configured")

    # 5. Random theo weight
    reward = random.choices(rewards, weights=[r.weight for r in rewards], k=1)[0]

    # 6. Cập nhật thưởng
    summary.spin_count = spin_left - 1

    if reward.codename == "coins":
        summary.coins = (summary.coins or 0) + reward.amount
    elif reward.codename.startswith("skin"):
        summary.skin_equipped = reward.codename
    else:
        if hasattr(summary, reward.codename):
            current_value = getattr(summary, reward.codename) or 0
            setattr(summary, reward.codename, current_value + reward.amount)
        else:
            raise HTTPException(status_code=500, detail=f"Unknown reward type: {reward.codename}")

    await db.commit()

    return {
        "status": "success",
        "reward": {
            "codename": reward.codename,
            "amount": reward.amount
        },
        "spin_count_left": summary.spin_count,
        "server_time": datetime.now(MYANMAR_TZ).isoformat()
    }

@router.get("/spin-rewards")
async def get_spin_rewards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SpinReward).order_by(SpinReward.position))
    rewards = result.scalars().all()

    return {
        "status": "success",
        "count": len(rewards),
        "rewards": [
            {
                "id": r.id,
                "codename": r.codename,
                "amount": r.amount,
                "weight": r.weight,
                "position": r.position
            }
            for r in rewards
        ]
    }

@router.put("/spin-rewards")
async def batch_update_spin_rewards(
    payload: List[SpinRewardPartialUpdate],
    db: AsyncSession = Depends(get_db)
):
    if len(payload) > 8:
        raise HTTPException(status_code=400, detail="Maximum 8 rewards allowed")

    # Lấy danh sách hiện tại
    result = await db.execute(select(SpinReward))
    existing_rewards = {r.id: r for r in result.scalars().all()}

    updated_ids = []
    for item in payload:
        if item.id in existing_rewards:
            reward = existing_rewards[item.id]
            if item.codename is not None:
                reward.codename = item.codename
            if item.amount is not None:
                reward.amount = item.amount
            if item.weight is not None:
                reward.weight = item.weight
            if item.position is not None:
                reward.position = item.position
            updated_ids.append(item.id)

    await db.commit()

    # Trả danh sách mới sau update
    result = await db.execute(select(SpinReward).order_by(SpinReward.position))
    rewards = result.scalars().all()

    return {
        "status": "success",
        "updated": updated_ids,
        "count": len(rewards),
        "rewards": [
            {
                "id": r.id,
                "codename": r.codename,
                "amount": r.amount,
                "weight": r.weight,
                "position": r.position
            }
            for r in rewards
        ]
    }