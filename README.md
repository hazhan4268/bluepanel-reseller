# BluePanel Reseller

FastAPI + Telegram Bot backend for a PasarGuard reseller/operator system.

## MVP features

- Provision a PasarGuard admin/operator after reseller purchase.
- Keep reseller wallet balance and price per GB.
- Monitor PasarGuard reseller usage.
- Deduct wallet balance based on real usage.
- Disable or enable reseller access when debt limits are reached.
- Web management panel for resellers, wallets, Telegram bot settings, and PasarGuard panel connections.
- Telegram webhook setup from the web panel.

## Architecture

```text
Telegram Bot / Admin Panel
        -> BluePanel FastAPI Backend
        -> PostgreSQL + Redis
        -> One or more PasarGuard panels
```

## Quick install

For a public repository:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/hazhan4268/bluepanel-reseller/main/quickstart.sh)
```

For a private repository, clone it after authenticating GitHub, then run:

```bash
bash quickstart.sh
```

## Manual start

```bash
cp .env.example .env
nano .env
docker compose up -d --build postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d --build
```

## Admin panel

Open:

```text
http://SERVER_IP:8080/panel?key=API_SECRET_KEY
```

The panel can manage:

- Telegram Bot Token
- Telegram Webhook URL and secret
- Set Webhook / Delete Webhook
- PasarGuard panel connections
- Reseller creation as PasarGuard operators
- Wallet credit/debit
- Manual usage monitor run

## Webhook URL format

After saving the bot token in the panel, set webhook URL like this:

```text
https://YOUR_DOMAIN/telegram/webhook/WEBHOOK_SECRET
```

The `WEBHOOK_SECRET` is shown/generated in the web panel.

## Health check

```text
http://SERVER_IP:8080/health
```

## Services

- api: FastAPI backend and web panel.
- bot: Telegram polling bot. Optional if webhook is used.
- usage-worker: periodic usage billing worker.
- postgres: database.
- redis: queue/cache placeholder.

## PasarGuard setup

Create a reseller role in PasarGuard with OWN scoped user permissions. You can set its role ID globally in `.env` or per PasarGuard panel inside the web panel.

```env
DEFAULT_PASARGUARD_ROLE_ID=3
```
