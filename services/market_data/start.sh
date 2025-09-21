#!/bin/sh
set -e

# Ensure timezone
export TZ=${TZ:-UTC}

# Run migrations (if alembic is available)
if command -v alembic >/dev/null 2>&1; then
  alembic upgrade head || true
fi

# Start API
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

