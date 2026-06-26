#!/usr/bin/env bash
set -e
APP_DIR=${APP_DIR:-/opt/bluepanel-reseller}
DOMAIN_VALUE=${1:-}
if [ -z "$DOMAIN_VALUE" ]; then
  echo "Usage: bash bluepanel-domain.sh panel.example.com"
  exit 1
fi
if echo "$DOMAIN_VALUE" | grep -Eq '^https?://|/|^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Use a real domain only. Example: panel.example.com"
  exit 1
fi
cd "$APP_DIR"
grep -q '^PUBLIC_DOMAIN=' .env && sed -i "s|^PUBLIC_DOMAIN=.*|PUBLIC_DOMAIN=$DOMAIN_VALUE|" .env || echo "PUBLIC_DOMAIN=$DOMAIN_VALUE" >> .env
grep -q '^PUBLIC_BASE_URL=' .env && sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://$DOMAIN_VALUE|" .env || echo "PUBLIC_BASE_URL=https://$DOMAIN_VALUE" >> .env
docker compose -f docker-compose.yml -f compose.ssl.yml up -d --build
echo "Done: https://$DOMAIN_VALUE/panel"
