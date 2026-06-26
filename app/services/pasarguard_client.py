from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings


class PasarGuardError(RuntimeError):
    pass


class PasarGuardClient:
    def __init__(self, base_url: str | None = None, admin_username: str | None = None, admin_secret: str | None = None) -> None:
        resolved_base_url = base_url or settings.pasarguard_base_url
        if not resolved_base_url:
            raise PasarGuardError('PasarGuard base URL is not configured')
        self.base_url = resolved_base_url.rstrip('/')
        self.admin_username = admin_username or settings.pasarguard_admin_username
        self.admin_secret = admin_secret or settings.pasarguard_admin_secret
        self._token: str | None = None
        self._token_created_at = 0.0
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0, verify=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def login(self) -> str:
        if self._token and time.time() - self._token_created_at < 1800:
            return self._token
        if not self.admin_username or not self.admin_secret:
            raise PasarGuardError('PasarGuard admin credential is not configured')
        response = await self._client.post('/api/admin/token', data={'username': self.admin_username, 'password': self.admin_secret}, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if response.status_code >= 400:
            raise PasarGuardError(f'PasarGuard login failed: {response.status_code} {response.text}')
        payload = response.json()
        self._token = payload.get('access_token')
        self._token_created_at = time.time()
        if not self._token:
            raise PasarGuardError('PasarGuard login response did not include access_token')
        return self._token

    async def _headers(self) -> dict[str, str]:
        token = await self.login()
        return {'Authorization': f'Bearer {token}'}

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop('headers', {}) or {}
        headers.update(await self._headers())
        response = await self._client.request(method, path, headers=headers, **kwargs)
        if response.status_code == 401:
            self._token = None
            headers.update(await self._headers())
            response = await self._client.request(method, path, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise PasarGuardError(f'{method} {path} failed: {response.status_code} {response.text}')
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def create_admin(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request('POST', '/api/admin', json=payload)

    async def modify_admin(self, username: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request('PUT', f'/api/admin/{username}', json=payload)

    async def disable_admin(self, username: str) -> dict[str, Any]:
        return await self.modify_admin(username, {'status': 'disabled'})

    async def enable_admin(self, username: str) -> dict[str, Any]:
        return await self.modify_admin(username, {'status': 'active'})

    async def disable_admin_users(self, username: str) -> dict[str, Any]:
        return await self.request('POST', f'/api/admin/{username}/users/disable')

    async def activate_admin_users(self, username: str) -> dict[str, Any]:
        return await self.request('POST', f'/api/admin/{username}/users/activate')

    async def get_admin_usage(self, username: str) -> Any:
        return await self.request('GET', f'/api/admin/{username}/usage')

    async def test_connection(self) -> Any:
        return await self.request('GET', '/api/admin')
