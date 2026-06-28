#!/usr/bin/env bash
set -euo pipefail

export FLASK_APP=superset

superset db upgrade

superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME:-admin}" \
  --firstname "${SUPERSET_ADMIN_FIRSTNAME:-Netflix}" \
  --lastname "${SUPERSET_ADMIN_LASTNAME:-BI}" \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@example.com}" \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true

superset init

exec superset run \
  --host 0.0.0.0 \
  --port 8088 \
  --with-threads
