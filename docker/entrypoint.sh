#!/bin/sh
set -e

MEDIA_NOTAUTH="/fastapi/media/notauth"
ASSETS_NOTAUTH="/fastapi/assets/notauth"

mkdir -p "$MEDIA_NOTAUTH"

if [ -d "$ASSETS_NOTAUTH" ]; then
  for file in "$ASSETS_NOTAUTH"/*; do
    name=$(basename "$file")
    if [ ! -f "$MEDIA_NOTAUTH/$name" ]; then
      cp "$file" "$MEDIA_NOTAUTH/$name"
    fi
  done
fi

# Apply pending Postgres migrations before serving (avoids UndefinedColumn 500s after deploy).
if [ "${SKIP_DB_MIGRATE:-0}" != "1" ] && command -v alembic >/dev/null 2>&1; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
