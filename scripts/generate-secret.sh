#!/usr/bin/env bash
# Generate a secure secret key for UAPK Gateway
set -euo pipefail

if command -v openssl &> /dev/null; then
    echo "SECRET_KEY=$(openssl rand -hex 32)"
elif command -v python3 &> /dev/null; then
    echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
else
    echo "ERROR: Need openssl or python3 to generate secret"
    exit 1
fi
