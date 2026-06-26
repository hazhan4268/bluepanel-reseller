# BluePanel Reseller

FastAPI + Telegram Bot backend for a PasarGuard reseller/operator system.

## MVP features

- Provision a PasarGuard admin/operator after reseller purchase.
- Keep reseller wallet balance and price per GB.
- Monitor PasarGuard reseller usage.
- Deduct wallet balance based on real usage.
- Disable or enable reseller access when debt limits are reached.
- Telegram Bot commands for balance and panel info.

## Architecture

```text
Telegram Bot / Admin API
        -> BluePanel FastAPI Backend
        -> PostgreSQL + Redis
        -> PasarGuard Panel API
```

## Quick start

```bash
cp .env.example .env
docker compose up -d --build
```

Health check:

```text
http://SERVER_IP:8080/health
```

## Services

- api: FastAPI backend.
- bot: Telegram bot.
- usage-worker: periodic usage billing worker.
- postgres: database.
- redis: queue/cache placeholder.

## PasarGuard setup

Create a reseller role in PasarGuard with OWN scoped user permissions, then set:

```env
DEFAULT_PASARGUARD_ROLE_ID=3
```
