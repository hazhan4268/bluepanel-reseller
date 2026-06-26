from fastapi import FastAPI

from app.config import settings
from app.api.routes_admin import router as admin_router
from app.api.routes_health import router as health_router

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(health_router)
app.include_router(admin_router)
