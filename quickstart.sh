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

require_domain() {
  source .env || true
  DOMAIN_VALUE="${PUBLIC_DOMAIN:-}"
  if [ -z "$DOMAIN_VALUE" ] || [ "$DOMAIN_VALUE" = "example.com" ]; then
    echo "Enter your real domain for SSL, for example panel.example.com:"
    read -r DOMAIN_VALUE
  fi
  if echo "$DOMAIN_VALUE" | grep -Eq '^https?://|/|^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "PUBLIC_DOMAIN must be a real domain only, not http, https, path, or IP. Example: panel.example.com"
    exit 1
  fi
  if grep -q '^PUBLIC_DOMAIN=' .env; then
    sed -i "s|^PUBLIC_DOMAIN=.*|PUBLIC_DOMAIN=$DOMAIN_VALUE|" .env
  else
    echo "PUBLIC_DOMAIN=$DOMAIN_VALUE" >> .env
  fi
  if grep -q '^PUBLIC_BASE_URL=' .env; then
    sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://$DOMAIN_VALUE|" .env
  else
    echo "PUBLIC_BASE_URL=https://$DOMAIN_VALUE" >> .env
  fi
  log "SSL domain: $DOMAIN_VALUE"
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

chmod +x "$APP_DIR/quickstart.sh"
ln -sf "$APP_DIR/quickstart.sh" /usr/local/bin/bluepanel-update
log "Update command installed: bluepanel-update"

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

require_domain
COMPOSE="docker compose -f docker-compose.yml -f compose.ssl.yml"

log "Cleaning old compose state"
$COMPOSE down --remove-orphans || true

log "Starting database"
$COMPOSE up -d --build postgres redis
sleep 8

log "Running database migrations"
$COMPOSE run --rm api alembic upgrade head

log "Starting BluePanel with HTTPS reverse proxy"
$COMPOSE up -d --build

$COMPOSE ps
log "Done. Open: https://$DOMAIN_VALUE/panel?key=API_SECRET_KEY"
