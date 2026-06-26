#!/usr/bin/env bash
set -e
APP_DIR=${APP_DIR:-/opt/bluepanel-reseller}
REPO_URL=${REPO_URL:-https://github.com/hazhan4268/bluepanel-reseller.git}
echo Installing BluePanel Reseller into $APP_DIR
apt update
apt install -y git python3 docker.io docker-compose-plugin
systemctl enable --now docker
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR" && git pull
else
  git clone "$REPO_URL" "$APP_DIR" && cd "$APP_DIR"
fi
[ -f .env ] || cp .env.example .env
docker compose up -d --build postgres redis
sleep 5
docker compose run --rm api alembic upgrade head
docker compose up -d --build
echo Done. Open http://SERVER_IP:8080/panel?key=API_SECRET_KEY
