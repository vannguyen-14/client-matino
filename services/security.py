import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.models import User

def generate_api_token(length: int = 32) -> str:
    """
    Sinh token hex an toàn.
    length: số byte trước khi hex (mặc định 32 → ra 64 ký tự hex)
    """
    return secrets.token_hex(length)

async def verify_api_token(user_id: int, token: str, db: AsyncSession) -> bool:
    """
    Xác thực token của user.
    Trả về True nếu hợp lệ, False nếu sai.
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.api_token == token)
    )
    user = result.scalars().first()
    return user is not None

async def assign_api_token(user: User, db: AsyncSession, length: int = 32) -> str:
    """
    Gán token mới cho user và lưu vào DB.
    Trả về token mới.
    """
    token = generate_api_token(length)
    user.api_token = token
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return token
