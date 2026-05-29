#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

if command -v npm >/dev/null 2>&1 && [ -f package-lock.json ]; then
  npm ci --include=dev
  npm run build:css
fi

python manage.py collectstatic --no-input --clear --ignore "src/*"
python manage.py migrate

if [ -n "$DEMO_PASSWORD" ]; then
  python manage.py seed_demo_data \
    --username "${DEMO_USERNAME:-Demo}" \
    --email "${DEMO_EMAIL:-demo@example.com}" \
    --password "$DEMO_PASSWORD" \
    --days "${DEMO_DAYS:-90}" \
    --clear
fi
