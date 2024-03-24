FROM python:3.12-alpine

ENV DJANGO_SETTINGS_MODULE=calls.settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

ARG POETRY_VERSION=1.8.2
RUN apk add --no-cache \
        gcc \
        libffi-dev \
        musl-dev \
    && wget -qO - https://install.python-poetry.org | python - \
    && apk del \
        gcc \
        musl-dev \
        libffi-dev
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml poetry.lock /app/
WORKDIR /app
ARG DEV_MODE=0
RUN poetry install $([ -z "$DEV_MODE" -o "$DEV_MODE" = '0' ] && echo '--without=dev')

COPY . /app/

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
