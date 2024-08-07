#!/bin/sh

set -e

if [ -z "$SECRET_KEY" ]; then
    echo "No SECRET_KEY set. Exiting."
    exit 1
fi

if [ "$DEV_MODE" = '0' ]; then
    DEV_MODE=
fi

cd "$(dirname "$0")"

wait-for-it --timeout 0 --service db:5432

if [ -z "$DEV_MODE" ]; then
    # Do this in the background
    ./manage.py collectstatic --noinput &
fi

./manage.py migrate

if [ "$DEV_MODE" ]; then
    if [ "$(./manage.py shell -c 'from api.models import User; print("" if User.objects.exists() else "1")')" = 1 ]; then
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
        exec gunicorn
    fi
else
    echo "Executing: $*"
    exec "$@"
fi
