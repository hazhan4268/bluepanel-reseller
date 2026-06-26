from fastapi import FastAPI

from app.api.routes_admin import router as admin_router
from app.api.routes_health import router as health_router
from app.api.routes_panel import router as panel_router
from app.api.routes_telegram import router as telegram_router
from app.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(health_router)
app.include_router(admin_router)
app.include_router(panel_router)
app.include_router(telegram_router)
