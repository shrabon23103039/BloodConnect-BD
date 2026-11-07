#!/bin/sh
set -eu

: "${PORT:?Render must provide PORT}"
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}"
