#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=${APP_DIR:-/opt/bluepanel-reseller}
REPO_URL=${REPO_URL:-https://github.com/hazhan4268/bluepanel-reseller.git}
COMPOSE_PLUGIN=/usr/local/lib/docker/cli-plugins/docker-compose

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo bash quickstart.sh"
  exit 1
fi

log() { echo "[BluePanel] $*"; }

install_compose_v2() {
  if docker compose version >/dev/null 2>&1; then
    return
  fi
  log "Installing Docker Compose v2 plugin"
  mkdir -p /usr/local/lib/docker/cli-plugins
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64|amd64) ASSET="x86_64" ;;
    aarch64|arm64) ASSET="aarch64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
  esac
  curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ASSET}" -o "$COMPOSE_PLUGIN"
  chmod +x "$COMPOSE_PLUGIN"
  docker compose version
}

log "Installing system packages"
apt update
apt install -y ca-certificates curl git python3 docker.io
systemctl enable --now docker
install_compose_v2

log "Fetching project"
mkdir -p "$(dirname "$APP_DIR")"
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR"
  git fetch origin main
  git reset --hard origin/main
else
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

if [ ! -f .env ]; then
  cp .env.example .env
  API_KEY=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)
  sed -i "s|^API_SECRET_KEY=.*|API_SECRET_KEY=$API_KEY|" .env
  log "Generated API_SECRET_KEY: $API_KEY"
fi

log "Cleaning old compose state"
docker compose down --remove-orphans || true

log "Starting database"
docker compose up -d --build postgres redis
sleep 8

log "Running database migrations"
docker compose run --rm api alembic upgrade head

log "Starting BluePanel services"
docker compose up -d --build

docker compose ps
log "Done. Open: http://SERVER_IP:8080/panel?key=API_SECRET_KEY"
