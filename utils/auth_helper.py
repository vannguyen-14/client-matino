import base64
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from models.models import User
from utils.response_helper import response_error  # 👈 import từ file mới

async def get_user_from_auth(auth: str, db):
    if not auth:
        return JSONResponse(
            status_code=400,
            content=response_error(400, "Missing parameter: auth")
        )

    try:
        decoded = base64.urlsafe_b64decode(auth.encode()).decode()
        msisdn, token = decoded.split(":", 1)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=response_error(400, "Invalid auth format")
        )

    result = await db.execute(select(User).where(User.msisdn == msisdn))
    user = result.scalars().first()

    if not user:
        return JSONResponse(
            status_code=404,
            content=response_error(404, "User not found")
        )

    if user.api_token != token:
        return JSONResponse(
            status_code=401,
            content=response_error(401, "Invalid token")
        )

    return user
