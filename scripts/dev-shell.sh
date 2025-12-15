#!/usr/bin/env bash
# Open a shell in the backend container
set -euo pipefail

exec docker compose exec backend bash
