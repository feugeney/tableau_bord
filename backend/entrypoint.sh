#!/bin/sh
set -e
# Seul le service « backend » applique les migrations (RUN_MIGRATIONS=1).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py initialiser
  python manage.py collectstatic --noinput
fi
exec "$@"
