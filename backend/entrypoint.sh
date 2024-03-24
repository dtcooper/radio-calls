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
fi

if [ "$#" = 0 ]; then
    if [ "$DEV_MODE" ]; then
        ./manage.py runserver
    else
        ./manage.py collectstatic --noinput
        echo "TODO"
    fi
else
    echo "Executing: $*"
    exec "$@"
fi
