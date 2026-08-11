#!/bin/bash

# Renew Let's Encrypt certificates and reload nginx.
# Idempotent: certbot only renews certificates near expiry.
#
# Schedule on the production host (example):
#   15 3 * * * /path/to/SRIS/scripts/renew_certs.sh >> /var/log/sris-renew.log 2>&1

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "🔐 Renewing certificates ($(date))..."

docker compose -f docker-compose.prod.yml --profile certbot run --rm certbot renew \
	--webroot --webroot-path=/var/www/certbot --quiet

docker compose -f docker-compose.prod.yml --profile certbot exec frontend nginx -s reload

echo "✅ Certificate renewal completed"
