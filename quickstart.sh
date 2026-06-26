#!/usr/bin/env bash
set -e

APP_DIR=${APP_DIR:-/opt/bluepanel-reseller}
REPO_URL=${REPO_URL:-https://github.com/hazhan4268/bluepanel-reseller.git}

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo bash quickstart.sh"
  exit 1
fi

echo "Installing BluePanel Reseller into $APP_DIR"
apt update
apt install -y git python3 docker.io

if apt-cache show docker-compose-plugin >/dev/null 2>&1; then
  apt install -y docker-compose-plugin
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  apt install -y docker-compose
  COMPOSE="docker-compose"
fi

systemctl enable --now docker

mkdir -p "$(dirname "$APP_DIR")"
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR" && git pull
else
  git clone "$REPO_URL" "$APP_DIR" && cd "$APP_DIR"
fi

[ -f .env ] || cp .env.example .env

$COMPOSE up -d --build postgres redis
sleep 5
$COMPOSE run --rm api alembic upgrade head
$COMPOSE up -d --build

echo "Done. Open http://SERVER_IP:8080/panel?key=API_SECRET_KEY"
