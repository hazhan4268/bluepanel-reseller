from fastapi import Header, HTTPException, status

from app.config import settings


async def require_admin_api_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.api_secret_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='API_SECRET_KEY is not configured')
    if x_admin_key != settings.api_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid admin key')
