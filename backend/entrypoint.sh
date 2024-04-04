#!/bin/sh

set -e

if [ -z "$SECRET_KEY" ]; then
    echo "No SECRET_KEY set. Exiting."
    exit 1
fi

if [ "$DEV_MODE" = '0' ]; then
    DEV_MODE=
fi

wait-for-it --timeout 0 --service db:5432

./manage.py migrate

if [ "$DEV_MODE" ]; then
    if [ "$(./manage.py shell -c 'from django.contrib.auth.models import User; print("" if User.objects.exists() else "1")')" = 1 ]; then
        DJANGO_SUPERUSER_PASSWORD=calls ./manage.py createsuperuser --noinput --username calls --email ''
    fi

    export PGHOST=db
    export PGUSER=postgres
    export PGPASSWORD=postgres
fi

if [ "$#" = 0 ]; then
    if [ "$DEV_MODE" ]; then
        exec ./manage.py runserver
    else
        NUM_GUNICORN_WORKERS="$(python -c 'import multiprocessing as m; print(m.cpu_count() * 2 + 1)')"

        ./manage.py collectstatic --noinput
        exec gunicorn \
                --forwarded-allow-ips '*' \
                -b 0.0.0.0:8000 \
                -w "$NUM_GUNICORN_WORKERS" \
                --capture-output \
                --access-logfile - \
            calls.wsgi
    fi
else
    echo "Executing: $*"
    exec "$@"
fi
