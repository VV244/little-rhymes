#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level ERROR
python manage.py migrate --noinput
python manage.py seed_demo
python manage.py seed_world_library

# Bounded real source checks create drafts only; provider failures are logged.
python manage.py sync_poetry_sources --limit 2
