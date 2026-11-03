#!/bin/sh
# ==============================================================================
# TalentAI Nginx Entrypoint — Strict HTTPS Pre-Flight Gate
# Enforces mandatory production TLS certificates before accepting traffic.
# ==============================================================================
set -e

CERT_PATH="/etc/nginx/ssl/talentai.crt"
KEY_PATH="/etc/nginx/ssl/talentai.key"

if [ ! -s "$CERT_PATH" ] || [ ! -s "$KEY_PATH" ]; then
    echo "==========================================================================" >&2
    echo "[TALENTAI DEPLOYMENT GATEWAY] CRITICAL: MISSING PRODUCTION TLS CERTIFICATES" >&2
    echo "==========================================================================" >&2
    echo "Production HTTPS is strictly mandatory. TalentAI refuses to start in an" >&2
    echo "unencrypted or partially configured state." >&2
    echo "" >&2
    echo "Required certificate files missing from /etc/nginx/ssl/:" >&2
    [ ! -s "$CERT_PATH" ] && echo "  - Missing: $CERT_PATH" >&2
    [ ! -s "$KEY_PATH" ]  && echo "  - Missing: $KEY_PATH" >&2
    echo "" >&2
    echo "Resolution Steps:" >&2
    echo "  1. Place your valid TLS certificate at: host ./nginx/ssl/talentai.crt" >&2
    echo "  2. Place your private key at:           host ./nginx/ssl/talentai.key" >&2
    echo "  3. Enforce secure file permissions:     chmod 600 ./nginx/ssl/talentai.key" >&2
    echo "  4. Launch the stack:                    docker compose up -d" >&2
    echo "==========================================================================" >&2
    exit 1
fi

# Validate Nginx configuration syntax with the installed certificates
echo "[TALENTAI] Validating Nginx configuration syntax..."
nginx -t

echo "[TALENTAI] Production TLS certificates verified. Launching Nginx..."
exec "$@"
