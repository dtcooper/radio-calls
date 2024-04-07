FROM python:3.12

ENV DJANGO_SETTINGS_MODULE=calls.settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    GEOIP2_LITE_CITY_DB_PATH=/usr/local/share/GeoLite2/GeoLite2-City.mmdb

# Path of GeoLite2 here adapted from Umami
RUN mkdir -p "$(dirname ${GEOIP2_LITE_CITY_DB_PATH})" \
    && cd "$(dirname ${GEOIP2_LITE_CITY_DB_PATH})" \
    && wget -qO - https://raw.githubusercontent.com/GitSquared/node-geolite2-redist/master/redist/GeoLite2-City.tar.gz \
        | tar xvz --strip-components 1

ARG POETRY_VERSION=1.8.2
RUN wget -qO - https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}"

ARG DEV_MODE=0
RUN if [ "$DEV_MODE" -a "$DEV_MODE" != '0' ]; then \
        echo "alias ls='ls --color=auto'" >> /root/.bashrc \
        && echo "alias rs='cd /app && ./manage.py runserver'" >> /root/.bashrc \
        && echo "alias sp='cd /app && ./manage.py shell_plus'" >> /root/.bashrc \
        && echo '. /etc/bash_completion' >> /root/.bashrc \
        && apt-get update \
        && apt-get upgrade -y \
        && apt-get install --no-install-recommends -y \
            bash-completion \
            iputils-ping \
            less \
            nano \
            netcat-openbsd \
            postgresql-client \
    ; fi

COPY pyproject.toml poetry.lock /app/
WORKDIR /app

RUN poetry install --no-root $([ -z "$DEV_MODE" -o "$DEV_MODE" = '0' ] && echo '--without=dev') \
    && if [ "$DEV_MODE" -a "$DEV_MODE" != 0 ]; then \
        # Download relevant verion's bash completion (in dev only)
        wget -qO /etc/bash_completion.d/django_bash_completion \
            "https://raw.githubusercontent.com/django/django/$(python -c 'import django; print(".".join(map(str, django.VERSION[:2])))')/extras/django_bash_completion" \
    ; fi

COPY . /app/

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
