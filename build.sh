#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

if command -v npm >/dev/null 2>&1 && [ -f package-lock.json ]; then
  npm ci
  npm run build:css
fi

python manage.py collectstatic --no-input
python manage.py migrate
