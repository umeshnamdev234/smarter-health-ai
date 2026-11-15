#!/bin/sh
# Container start: apply migrations, optionally seed sample doctors, start the API.
set -e

echo "Applying database migrations..."
alembic upgrade head

if [ "${SEED_SAMPLE_DOCTORS:-false}" = "true" ]; then
  python scripts/import_doctors.py data/doctors.sample.json --if-empty
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
