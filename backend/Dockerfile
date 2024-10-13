FROM python:3.12-bookworm

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

ARG POETRY_VERSION=1.8.3
RUN wget -qO - https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}"

ARG DEBUG=0
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install --no-install-recommends -y \
        ffmpeg \
        sox \
    && rm -rf /var/lib/apt/lists/* \
    && if [ "$DEBUG" -a "$DEBUG" != '0' ]; then \
        echo "alias ls='ls --color=auto'" >> /root/.bashrc \
        && echo "alias rs='./manage.py runserver'" >> /root/.bashrc \
        && echo "alias rsp='ALLOW_MTURK_PRODUCTION_ACCESS=1 ./manage.py runserver'" >> /root/.bashrc \
        && echo "alias sp='./manage.py shell_plus'" >> /root/.bashrc \
        && echo "alias spp='ALLOW_MTURK_PRODUCTION_ACCESS=1 ./manage.py shell_plus'" >> /root/.bashrc \
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

RUN poetry install --no-root $([ -z "$DEBUG" -o "$DEBUG" = '0' ] && echo '--without=dev') \
    && if [ "$DEBUG" -a "$DEBUG" != 0 ]; then \
        # Download relevant verion's bash completion (in dev only)
        wget -qO /etc/bash_completion.d/django_bash_completion \
            "https://raw.githubusercontent.com/django/django/$(python -c 'import django; print(".".join(map(str, django.VERSION[:2])))')/extras/django_bash_completion" \
    ; fi

COPY . /app/

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []

ARG GIT_REV=unknown \
    BUILD_TIME=2000-01-01T00:00:00Z  # Some random parsable default

ENV GIT_REV="${GIT_REV}" \
    BUILD_TIME="${BUILD_TIME}"
