from fastapi import APIRouter, Depends

from app.api.deps import require_admin_api_key

router = APIRouter(prefix='/api/admin', tags=['admin'], dependencies=[Depends(require_admin_api_key)])


@router.get('/ping')
async def admin_ping() -> dict[str, str]:
    return {'status': 'admin-ok'}
