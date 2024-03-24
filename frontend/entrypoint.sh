#!/bin/sh

if [ "$DEV_MODE" = '0' ]; then
    DEV_MODE=
fi

if [ "$#" = 0 ]; then
    if [ "$DEV_MODE" ]; then
        exec npm run dev
    else
        npm install
        exec npm run build
    fi
else
    echo "Executing: $*"
    exec "$@"
fi
