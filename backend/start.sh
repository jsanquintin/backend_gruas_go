#!/bin/sh
set -eu
: "${DATABASE_URL:?Defina DATABASE_URL (PostgreSQL de Railway)}"
: "${JWT_SECRET:?Defina JWT_SECRET (secreto privado)}"

# Convertir URL de Railway para usar el driver psycopg3, sin mostrarla en logs.
export DATABASE_URL="$(python - <<'PY'
import os
v=os.environ['DATABASE_URL']
if v.startswith('postgres://'): v='postgresql+psycopg://'+v[len('postgres://'):]
elif v.startswith('postgresql://'): v='postgresql+psycopg://'+v[len('postgresql://'):]
print(v)
PY
)"

alembic upgrade head
if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
  python -m scripts.bootstrap_admin
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips '*'
