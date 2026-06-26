# Installation

1. Clone the repository to your server.
2. Copy `.env.example` to `.env`.
3. Fill API key, Telegram bot settings, and PasarGuard details.
4. Start the stack with Docker Compose.
5. Run Alembic migrations.
6. Open `/panel?key=API_SECRET_KEY` in your browser.

Main panel URL:

```text
http://YOUR_SERVER_IP:8080/panel?key=API_SECRET_KEY
```

The web panel can manage:

- Telegram bot token
- Telegram webhook URL
- PasarGuard panel connections
- Resellers
- Wallet balance
- Usage monitor
